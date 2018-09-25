from threading import local
from urllib.parse import urlsplit, urlunsplit

from django.utils.encoding import iri_to_uri
from django.utils.functional import lazy
from django.utils.translation import override

from .exceptions import NoReverseMatch, Resolver404
from .resolvers import get_ns_resolver, get_resolver
from .utils import get_callable

# SCRIPT_NAME prefixes for each thread are stored here. If there's no entry for
# 每个线程的脚本前缀将存储在这里,如果没有进入当前线程的入口(), 它被假设为空的
# the current thread (which is the only one we ever access), it is assumed to
# be empty.
_prefixes = local()

# Overridden URLconfs for each thread are stored here.
_urlconfs = local()


def resolve(path, urlconf=None):
    """
    para: path: 需要解析的路径
    para: urlconf: url配置
    """
    # 如果urlconf为None, 使用get_urlconf获取urlconf
    if urlconf is None:
        urlconf = get_urlconf()
    # 通过get_resolver, 之后调用resolve返回一个解析的对象...
    # TODO
    return get_resolver(urlconf).resolve(path)


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    """
    para: viewname: 视图函数名称
    para: urlconf: url配置, 默认为None
    para: args: 通过序列形式传入的参数, 默认为None
    para: kwargs: 通过字典形式传入的参数, 默认为None
    para: current_app: current_app, 默认为None
    """
    if urlconf is None:
        # 如果没有urlconf,通过get_urlconf获取
        urlconf = get_urlconf()
    # 通过urlconf获取resolver
    resolver = get_resolver(urlconf)
    # args为None的话赋值为空列表
    args = args or []
    # ksargs为空的话赋值为空字典
    kwargs = kwargs or {}

    # 使用get_script_prefix获取脚本前缀
    prefix = get_script_prefix()

    # 如果viewname不是字符串, view直接饮用viewname
    if not isinstance(viewname, str):
        view = viewname
    else:
        # 如果viewname是字符串, 通过字符串操作获取view
        # 通过:切分字符串
        parts = viewname.split(':')
        # 翻转parts
        parts.reverse()
        # view 是parts的第一个元素
        view = parts[0]
        # path 是parts中1到最后一个元素
        path = parts[1:]

        # 如果有current_app, 使用字符串操作解析
        if current_app:
            current_path = current_app.split(':')
            current_path.reverse()
        else:
            # 没有的current_app的话, current_path为None
            current_path = None

        resolved_path = []
        ns_pattern = ''
        ns_converters = {}
        while path:
            ns = path.pop()
            current_ns = current_path.pop() if current_path else None
            # Lookup the name to see if it could be an app identifier.
            try:
                app_list = resolver.app_dict[ns]
                # Yes! Path part matches an app in the current Resolver.
                if current_ns and current_ns in app_list:
                    # If we are reversing for a particular app, use that
                    # namespace.
                    ns = current_ns
                elif ns not in app_list:
                    # The name isn't shared by one of the instances (i.e.,
                    # the default) so pick the first instance as the default.
                    ns = app_list[0]
            except KeyError:
                pass

            if ns != current_ns:
                current_path = None

            try:
                extra, resolver = resolver.namespace_dict[ns]
                resolved_path.append(ns)
                ns_pattern = ns_pattern + extra
                ns_converters.update(resolver.pattern.converters)
            except KeyError as key:
                if resolved_path:
                    raise NoReverseMatch(
                        "%s is not a registered namespace inside '%s'" %
                        (key, ':'.join(resolved_path))
                    )
                else:
                    raise NoReverseMatch("%s is not a registered namespace" % key)
        if ns_pattern:
            resolver = get_ns_resolver(ns_pattern, resolver, tuple(ns_converters.items()))

    return iri_to_uri(resolver._reverse_with_prefix(view, prefix, *args, **kwargs))


reverse_lazy = lazy(reverse, str)


def clear_url_caches():
    get_callable.cache_clear()
    get_resolver.cache_clear()
    get_ns_resolver.cache_clear()


def set_script_prefix(prefix):
    """
    Set the script prefix for the current thread.
    为当前的线程设置脚本前缀
    """
    if not prefix.endswith('/'):
        prefix += '/'
    _prefixes.value = prefix


def get_script_prefix():
    """
    Return the currently active script prefix. Useful for client code that
    wishes to construct their own URLs manually (although accessing the request
    instance is normally going to be a lot cleaner).
    """
    return getattr(_prefixes, "value", '/')


def clear_script_prefix():
    """
    Unset the script prefix for the current thread.
    """
    try:
        del _prefixes.value
    except AttributeError:
        pass


def set_urlconf(urlconf_name):
    """
    Set the URLconf for the current thread (overriding the default one in
    settings). If urlconf_name is None, revert back to the default.
    """
    if urlconf_name:
        _urlconfs.value = urlconf_name
    else:
        if hasattr(_urlconfs, "value"):
            del _urlconfs.value


def get_urlconf(default=None):
    """
    Return the root URLconf to use for the current thread if it has been
    changed from the default one.
    """
    return getattr(_urlconfs, "value", default)


def is_valid_path(path, urlconf=None):
    """
    Return True if the given path resolves against the default URL resolver,
    False otherwise. This is a convenience method to make working with "is
    this a match?" cases easier, avoiding try...except blocks.
    """
    try:
        resolve(path, urlconf)
        return True
    except Resolver404:
        return False


def translate_url(url, lang_code):
    """
    Given a URL (absolute or relative), try to get its translated version in
    the `lang_code` language (either by i18n_patterns or by translated regex).
    Return the original URL if no translated version is found.
    """
    parsed = urlsplit(url)
    try:
        match = resolve(parsed.path)
    except Resolver404:
        pass
    else:
        to_be_reversed = "%s:%s" % (match.namespace, match.url_name) if match.namespace else match.url_name
        with override(lang_code):
            try:
                url = reverse(to_be_reversed, args=match.args, kwargs=match.kwargs)
            except NoReverseMatch:
                pass
            else:
                url = urlunsplit((parsed.scheme, parsed.netloc, url, parsed.query, parsed.fragment))
    return url
