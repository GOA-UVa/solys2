try:
    from . import response
    from . import connection
    from . import common
    from . import solys2
    from . import automation
except:
    from solys2 import connection
    from solys2 import response
    from solys2 import common
    from solys2 import automation
    from solys2 import solys2
