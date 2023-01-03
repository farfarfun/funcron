from.core import blue_print


@blue_print.app_errorhandler(404)
def page_not_found(e):
    return 'page not found'


@blue_print.app_errorhandler(500)
def internal_server_error(e):
    return 'system err'
