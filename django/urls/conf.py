"""Functions for use in URLsconfs."""
from functools import partial
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured

from .resolvers import (
    LocalePrefixPattern, RegexPattern, RoutePattern, URLPattern, URLResolver,
)


def include(arg, namespace=None):
    app_name = None
    if isinstance(arg, tuple):

        # arg是一个元组的时候, 执行如下代码
        # Callable returning a namespace hint.
        try:
            # 从元组中解析出urlconf_module, app_name
            urlconf_module, app_name = arg
            # 如果arg中的元素数量不是两个,会抛出ValueError
        except ValueError:
            # 如果解析元组抛出了ValueError异常, 执行如下代码
            if namespace:
                # 如果有namespace参数, 抛出ImproperlyConfigured(不合适的配置)
                raise ImproperlyConfigured(
                    'Cannot override the namespace for a dynamic module that '
                    'provides a namespace.'
                )
            raise ImproperlyConfigured(
                'Passing a %d-tuple to include() is not supported. Pass a '
                '2-tuple containing the list of patterns and app_name, and '
                'provide the namespace argument to include() instead.' % len(arg)
            )
    else:
        # 如果args不是一个元组,执行如下代码
        # No namespace hint - use manually provided namespace.
        # 没有namespace提示, 使用手动提供的namespace
        urlconf_module = arg


    if isinstance(urlconf_module, str):
        # 如果urlconf_module是字符串, 导入对应的模块
        urlconf_module = import_module(urlconf_module)
    # 在模块中获取到urlpatterns
    patterns = getattr(urlconf_module, 'urlpatterns', urlconf_module)
    # 在
    app_name = getattr(urlconf_module, 'app_name', app_name)
    if namespace and not app_name:
        raise ImproperlyConfigured(
            'Specifying a namespace in include() without providing an app_name '
            'is not supported. Set the app_name attribute in the included '
            'module, or pass a 2-tuple containing the list of patterns and '
            'app_name instead.',
        )
    namespace = namespace or app_name
    # Make sure the patterns can be iterated through (without this, some
    # testcases will break).
    if isinstance(patterns, (list, tuple)):
        for url_pattern in patterns:
            pattern = getattr(url_pattern, 'pattern', None)
            if isinstance(pattern, LocalePrefixPattern):
                raise ImproperlyConfigured(
                    'Using i18n_patterns in an included URLconf is not allowed.'
                )
    return (urlconf_module, app_name, namespace)


def _path(route, view, kwargs=None, name=None, Pattern=None):
    if isinstance(view, (list, tuple)):
        # For include(...) processing.
        pattern = Pattern(route, is_endpoint=False)
        urlconf_module, app_name, namespace = view
        return URLResolver(
            pattern,
            urlconf_module,
            kwargs,
            app_name=app_name,
            namespace=namespace,
        )
    elif callable(view):
        pattern = Pattern(route, name=name, is_endpoint=True)
        return URLPattern(pattern, view, kwargs, name)
    else:
        raise TypeError('view must be a callable or a list/tuple in the case of include().')


path = partial(_path, Pattern=RoutePattern)
re_path = partial(_path, Pattern=RegexPattern)
