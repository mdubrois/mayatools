import tempfile

from maya import cmds

from .. import context


settings = {
    'attrs': {
        'defaultRenderGlobals.imageFormat': 8, # JPEG.
        'defaultResolution.width': 1280,
        'defaultResolution.height': 720,
        'defaultResolution.deviceAspectRatio': 1280.0 / 720,
        'defaultResolution.pixelAspect': 1.0,
        'defaultResolution.dotsPerInch': 72,
        'defaultResolution.pixelDensityUnits': 0,
    },
    'camera_attrs': {
        'horizontalFilmOffset': 0,
        'verticalFilmOffset': 0,
    },
    'camera': {
        'displayFilmGate': 0,
        'displayResolution': 1,
        'overscan': 1,
    },
}


def playblast(**kwargs):

    # Extract the camera from the active view.
    current_panel = cmds.getPanel(withFocus=True)
    panel_type = cmds.getPanel(typeOf=current_panel) 
    if panel_type == 'modelPanel':
        camera = cmds.modelPanel(current_panel, query=True, camera=True)
        camera_attrs = dict((camera + '.' + k, v) for k, v in settings['camera_attrs'].iteritems())
    else:
        cmds.warning('Current panel is not a modelling panel; playblasts will not correctly setup the camera')
        camera = None
        camera_attrs = {}
    
    # These should really be controlled elsewhere...
    kwargs.setdefault('widthHeight', (1280, 720))
    kwargs.setdefault('offScreen', True)
    kwargs.setdefault('forceOverwrite', True)
    kwargs.setdefault('percent', 100)
    
    # So much state! Can we have Python2.7 now?
    with context.attrs(settings['attrs'], camera_attrs):
        with context.command(cmds.camera, camera, edit=True, **(settings['camera'] if camera else {})):
            with context.command(cmds.currentUnit, linear='cm', time='film'):
                return cmds.playblast(**kwargs)


def screenshot(frame=None, **kwargs):
    path = tempfile.NamedTemporaryFile(suffix=".jpg", prefix="screenshot.", delete=False).name
    frame = cmds.currentTime(q=True) if frame is None else frame
    playblast(
        frame=[frame],
        format='image',
        completeFilename=path,
        viewer=False,
        p=100,
        framePadding=4, # ??
    )
    return path

