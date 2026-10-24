/*
 * Battery level for a power-path charger: see dts/bindings/sensor/urchin,battery-power-aware.yaml.
 *
 * The BQ24073 powers the system from its input whenever input power is present, so VDDH
 * (what zmk,battery-nrf-vddh measures) sits at the charger's regulated 4.4 V instead of
 * the cell voltage, and ZMK would report a full battery the moment the half is docked.
 * This driver reads the charger's PGOOD and CHG outputs (through Schottky diodes to
 * GPIOs with pull-ups) at each sample and decides which number to report.
 *
 * The last level measured on battery is kept in GPREGRET2, a retention register that
 * survives soft resets and the reset that wakes the chip from System OFF (ZMK's deep
 * sleep), so a half that wakes or restarts while charging still reports it. Neither ZMK
 * nor Zephyr uses GPREGRET2 (ZMK's boot-mode flag and the Adafruit bootloader use
 * GPREGRET). Only a power loss (battery disconnected) clears it.
 *
 * SPDX-License-Identifier: MIT
 */

#define DT_DRV_COMPAT urchin_battery_power_aware

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/sensor.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <hal/nrf_power.h>

LOG_MODULE_REGISTER(battery_power_aware, CONFIG_SENSOR_LOG_LEVEL);

#define FULL_MV 4200
#define EMPTY_MV 3450
#define RETAINED_REG 1          /* GPREGRET2 */
#define RETAINED_VALID 0x80     /* bit 7: a level is stored in bits 0-6 */
#define CHG_SAMPLES 6           /* CHG blinks at 2 Hz on a fault: sample it over 600 ms */
#define CHG_SAMPLE_MS 100

struct bpa_config {
    const struct device *battery;
    struct gpio_dt_spec power_good;
    struct gpio_dt_spec charging;
};

struct bpa_data {
    int32_t millivolts;
    int32_t state_of_charge;
    bool have_battery_reading; /* a level measured without input power */
    int32_t battery_millivolts;
    int32_t battery_state_of_charge;
    bool was_complete; /* the previous sample saw input power and no charging */
};

/* The inverse of ZMK's lithium_ion_mv_to_pct(), for a level restored from GPREGRET2. */
static int32_t pct_to_mv(int32_t pct) {
    if (pct >= 100) {
        return FULL_MV;
    }
    if (pct <= 0) {
        return EMPTY_MV;
    }
    return (pct + 459) * 15 / 2;
}

static void retain_level(int32_t pct) {
    nrf_power_gpregret_set(NRF_POWER, RETAINED_REG, RETAINED_VALID | (uint8_t)CLAMP(pct, 0, 100));
}

/* Reads an open-drain status line, active-low through a Schottky diode, `samples` times
 * `interval_ms` apart with the pull-up on, then disconnects the pin so the pull-up never
 * draws current between samples. Returns 1 if any read was active, 0 if none, <0 on error. */
static int read_status(const struct gpio_dt_spec *spec, int samples, int interval_ms) {
    int rc = gpio_pin_configure_dt(spec, GPIO_INPUT);
    if (rc != 0) {
        return rc;
    }
    int active = 0;
    for (int i = 0; i < samples && rc >= 0; i++) {
        if (i > 0) {
            k_msleep(interval_ms);
        } else {
            k_busy_wait(50); /* the pull-up (~13 kOhm) charges the pin and the diode */
        }
        rc = gpio_pin_get_dt(spec);
        active |= rc > 0;
    }
    gpio_pin_configure(spec->port, spec->pin, GPIO_DISCONNECTED);
    return rc < 0 ? rc : active;
}

static int fetch_battery(const struct device *dev) {
    const struct bpa_config *cfg = dev->config;
    struct bpa_data *data = dev->data;
    struct sensor_value mv, soc;

    if (!device_is_ready(cfg->battery)) {
        return -ENODEV;
    }
    int rc = sensor_sample_fetch_chan(cfg->battery, SENSOR_CHAN_ALL);
    if (rc != 0) {
        return rc;
    }
    rc = sensor_channel_get(cfg->battery, SENSOR_CHAN_GAUGE_VOLTAGE, &mv);
    if (rc == 0) {
        rc = sensor_channel_get(cfg->battery, SENSOR_CHAN_GAUGE_STATE_OF_CHARGE, &soc);
    }
    if (rc != 0) {
        return rc;
    }
    data->millivolts = mv.val1 * 1000 + mv.val2 / 1000;
    data->state_of_charge = soc.val1;
    return 0;
}

static int bpa_sample_fetch(const struct device *dev, enum sensor_channel chan) {
    const struct bpa_config *cfg = dev->config;
    struct bpa_data *data = dev->data;

    if (chan != SENSOR_CHAN_ALL && chan != SENSOR_CHAN_GAUGE_VOLTAGE && chan != SENSOR_CHAN_VOLTAGE &&
        chan != SENSOR_CHAN_GAUGE_STATE_OF_CHARGE) {
        return -ENOTSUP;
    }

    int power_good = read_status(&cfg->power_good, 1, 0);
    if (power_good < 0) {
        LOG_WRN("Can't read PGOOD (%d); reporting the raw reading", power_good);
        return fetch_battery(dev);
    }
    if (!power_good) {
        data->was_complete = false;
        int rc = fetch_battery(dev);
        if (rc == 0) {
            data->have_battery_reading = true;
            data->battery_millivolts = data->millivolts;
            data->battery_state_of_charge = data->state_of_charge;
            retain_level(data->state_of_charge);
        }
        return rc;
    }

    /* Input power. Charging unless CHG stayed inactive over the whole window, and only
     * "complete" if the previous sample said so too: that rides out the charger's start-up
     * checks and pogo-pin bounce right after docking. */
    int charging = read_status(&cfg->charging, CHG_SAMPLES, CHG_SAMPLE_MS);
    bool complete = charging == 0;
    bool report_full = complete && data->was_complete;
    data->was_complete = complete;
    if (report_full) {
        LOG_DBG("Input power, not charging: charge complete");
        data->millivolts = FULL_MV;
        data->state_of_charge = 100;
        return 0;
    }
    if (data->have_battery_reading) {
        LOG_DBG("Charging: holding %d%% from before input power", data->battery_state_of_charge);
        data->millivolts = data->battery_millivolts;
        data->state_of_charge = data->battery_state_of_charge;
        return 0;
    }
    /* Charging and no level measured on battery since the last power loss: all there is
     * to report is VDDH, which reads full (firmware/README.md). */
    return fetch_battery(dev);
}

static int bpa_channel_get(const struct device *dev, enum sensor_channel chan, struct sensor_value *val) {
    const struct bpa_data *data = dev->data;

    switch (chan) {
    case SENSOR_CHAN_GAUGE_VOLTAGE:
    case SENSOR_CHAN_VOLTAGE:
        val->val1 = data->millivolts / 1000;
        val->val2 = (data->millivolts % 1000) * 1000;
        return 0;
    case SENSOR_CHAN_GAUGE_STATE_OF_CHARGE:
        val->val1 = data->state_of_charge;
        val->val2 = 0;
        return 0;
    default:
        return -ENOTSUP;
    }
}

static const struct sensor_driver_api bpa_api = {
    .sample_fetch = bpa_sample_fetch,
    .channel_get = bpa_channel_get,
};

static int bpa_init(const struct device *dev) {
    const struct bpa_config *cfg = dev->config;
    struct bpa_data *data = dev->data;

    if (!gpio_is_ready_dt(&cfg->power_good) || !gpio_is_ready_dt(&cfg->charging)) {
        LOG_ERR("Status GPIOs not ready");
        return -ENODEV;
    }
    gpio_pin_configure(cfg->power_good.port, cfg->power_good.pin, GPIO_DISCONNECTED);
    gpio_pin_configure(cfg->charging.port, cfg->charging.pin, GPIO_DISCONNECTED);

    uint32_t retained = nrf_power_gpregret_get(NRF_POWER, RETAINED_REG);
    if ((retained & RETAINED_VALID) && (retained & 0x7f) <= 100) {
        data->have_battery_reading = true;
        data->battery_state_of_charge = retained & 0x7f;
        data->battery_millivolts = pct_to_mv(data->battery_state_of_charge);
    }
    return 0;
}

#define BPA_INIT(n)                                                                                \
    static const struct bpa_config bpa_config_##n = {                                              \
        .battery = DEVICE_DT_GET(DT_INST_PHANDLE(n, battery)),                                     \
        .power_good = GPIO_DT_SPEC_INST_GET(n, power_good_gpios),                                  \
        .charging = GPIO_DT_SPEC_INST_GET(n, charging_gpios),                                      \
    };                                                                                             \
    static struct bpa_data bpa_data_##n;                                                           \
    DEVICE_DT_INST_DEFINE(n, bpa_init, NULL, &bpa_data_##n, &bpa_config_##n, POST_KERNEL,          \
                          CONFIG_SENSOR_INIT_PRIORITY, &bpa_api);

DT_INST_FOREACH_STATUS_OKAY(BPA_INIT)
