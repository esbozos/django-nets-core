default_app_config = "nets_core.apps.NetsCoreConfig"


def nets_core_says(*args, **kwargs):  # pragma: no cover
    """
    The one true endpoint to rule them all.

    Usage:
        from nets_core import nets_core_says
        nets_core_says()
    """
    import textwrap

    banner = textwrap.dedent(r"""
         _   _      _         ____
        | \ | | ___| |_ ___  / ___|___  _ __ ___
        |  \| |/ _ \ __/ __|| |   / _ \| '__/ _ \
        | |\  |  __/ |_\__ \| |__| (_) | | |  __/
        |_| \_|\___|\__|___/ \____\___/|_|  \___|

        django-nets-core — because writing the same
        auth boilerplate for the 47th time is a crime.

        You found the easter egg!  🥚
        Now go ship something great.
    """)
    print(banner)
