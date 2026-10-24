"""Offscreen PNG renders of build123d shapes with VTK, for reports and for checking a design
without a GUI."""

import vtk

VIEWS = {
    # name: (direction from the target to the camera, view-up)
    "iso": ((1, -1.4, 1.1), (0, 0, 1)),
    "iso-back": ((-1, 1.4, 1.1), (0, 0, 1)),
    "top": ((0, 0, 1), (0, 1, 0)),
    "bottom": ((0, 0, -1), (0, 1, 0)),
    "under": ((0.8, -1.2, -1.3), (0, 0, 1)),
    "front": ((0, -1, 0.25), (0, 0, 1)),
    "inner": ((1, 0, 0.3), (0, 0, 1)),
    "outer": ((-1, 0, 0.3), (0, 0, 1)),
}

COLORS = {
    "case": (0.93, 0.55, 0.20),
    "cover": (0.25, 0.55, 0.85),
    "board": (0.10, 0.45, 0.20),
    "parts": (0.35, 0.35, 0.38),
    "tray": (0.80, 0.80, 0.82),
    "dock": (0.10, 0.30, 0.60),
    "pins": (0.85, 0.70, 0.20),
}


def polydata(shape, tolerance=0.05):
    verts, tris = shape.tessellate(tolerance, 0.3)
    points = vtk.vtkPoints()
    for v in verts:
        points.InsertNextPoint(v.X, v.Y, v.Z)
    cells = vtk.vtkCellArray()
    for t in tris:
        cells.InsertNextCell(3)
        for i in t:
            cells.InsertCellPoint(i)
    pd = vtk.vtkPolyData()
    pd.SetPoints(points)
    pd.SetPolys(cells)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(35)
    normals.Update()
    return normals.GetOutput()


def render(items, path, view="iso", size=(1600, 1100), zoom=1.0):
    """items: [(shape, color name or rgb, opacity)]. Writes a PNG."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for shape, color, opacity in items:
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata(shape))
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*(COLORS.get(color, color) if isinstance(color, str) else color))
        prop.SetOpacity(opacity)
        prop.SetSpecular(0.15)
        ren.AddActor(actor)
        edges = vtk.vtkFeatureEdges()
        edges.SetInputData(mapper.GetInput())
        edges.BoundaryEdgesOff()
        edges.FeatureEdgesOn()
        edges.SetFeatureAngle(35)
        edges.ManifoldEdgesOff()
        edges.NonManifoldEdgesOff()
        em = vtk.vtkPolyDataMapper()
        em.SetInputConnection(edges.GetOutputPort())
        em.ScalarVisibilityOff()
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        ea.GetProperty().SetColor(0.1, 0.1, 0.1)
        ea.GetProperty().SetOpacity(min(1.0, opacity + 0.2))
        ea.GetProperty().SetLineWidth(1.0)
        ren.AddActor(ea)
    direction, up = VIEWS[view]
    cam = ren.GetActiveCamera()
    cam.SetFocalPoint(0, 0, 0)
    cam.SetPosition(*direction)
    cam.SetViewUp(*up)
    if view in ("top", "bottom"):
        cam.ParallelProjectionOn()
    ren.ResetCamera()
    cam.Zoom(zoom)
    light = vtk.vtkLight()
    light.SetLightTypeToCameraLight()
    light.SetPosition(0.4, 0.6, 1)
    ren.AddLight(light)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.SetMultiSamples(8)
    win.AddRenderer(ren)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(grab.GetOutputPort())
    writer.Write()
