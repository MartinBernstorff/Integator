import logging

format = "%(asctime)s \t%(levelname)s \t%(name)s \t%(message)s"
date_fmt = "%H:%M:%S"


def init_log(debug: bool, quiet: bool):
    # feat: get colored logging working
    log_level = logging.ERROR if quiet else logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format=format,
        datefmt=date_fmt,
    )
