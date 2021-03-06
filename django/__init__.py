from django.utils.version import get_version

VERSION = (2, 2, 0, 'alpha', 0)
# __version__属性获得一个符合标准的版本属性
__version__ = get_version(VERSION)


def setup(set_prefix=True):
    """
    Configure the settings (this happens as a side effect of accessing the
    first setting), configure logging and populate the app registry.
    Set the thread-local urlresolvers script prefix if `set_prefix` is True.
    配置设置内容(这是进入第一次设置的副作用), 配置日志并填充app注册表.
    如果set_prefix为True的话, 为本地线程的urlresolvers脚本添加前缀
    """
    from django.apps import apps
    from django.conf import settings
    from django.urls import set_script_prefix
    from django.utils.log import configure_logging

    # default LOGGING_CONFIG = 'logging.config.dictConfig'
    # from logging.config import dictConfig
    # 这一步会将写入的日志设置配置完成
    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
    
    # 设置脚本前缀
    if set_prefix:
        set_script_prefix(
            '/' if settings.FORCE_SCRIPT_NAME is None else settings.FORCE_SCRIPT_NAME
        )
    # 填充注册表
    apps.populate(settings.INSTALLED_APPS)
