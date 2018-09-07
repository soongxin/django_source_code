import functools
from importlib import import_module

from django.core.exceptions import ViewDoesNotExist
from django.utils.module_loading import module_has_submodule


# 把相对耗时的函数结果进行缓存, 避免传入相同的参数重复计算, 缓存不会无限增长,不用的缓存会被释放
@functools.lru_cache(maxsize=None)
def get_callable(lookup_view):
    """
    Return a callable corresponding to lookup_view.
    返回一个与lookup_view一致的可调用对象
    * If lookup_view is already a callable, return it.
    * 如果lookup_view 是可调用对象, 将其返回
    * If lookup_view is a string import path that can be resolved to a callable,
    * 如果lookup_view 是可以被解析成可调用对象的字符串
      import that callable and return it, otherwise raise an exception
      将对应的可调用对象导入, 并返回出去, 否则抛出异常
      (ImportError or ViewDoesNotExist).
    """
    # 判断lookup_view是否是可调用对象, 是则返回出去
    if callable(lookup_view):
        return lookup_view

    # 如果不是可调用对象, 而且不是字符串, 抛出异常ViewDoesNotExist
    if not isinstance(lookup_view, str):
        raise ViewDoesNotExist("'%s' is not a callable or a dot-notation path" % lookup_view)

    # 如果是字符串, 通过调用get_mod_func解析出来mod_name和 func_name
    mod_name, func_name = get_mod_func(lookup_view)
    # 如果没有获取到func_name, 即在lookup_view中没有'.', 抛出异常ImportError
    if not func_name:  # No '.' in lookup_view
        raise ImportError("Could not import '%s'. The path must be fully qualified." % lookup_view)

    # 上述验证通过, 尝试导入mode_name
    try:
        mod = import_module(mod_name)
    except ImportError:
        # 如果出现ImportError, 使用get_mod_func在mod_name中解析parentmod和submod
        parentmod, submod = get_mod_func(mod_name)
        # 如果解析除了submod, 并且module_has_submodule返回值为False, 抛出ViewDoesExist异常
        if submod and not module_has_submodule(import_module(parentmod), submod):
            raise ViewDoesNotExist(
                "Could not import '%s'. Parent module %s does not exist." %
                (lookup_view, mod_name)
            )
        else:
            raise

    # mod成功导入的话,执行如下代码
    else:
        try:
            # 从mod中获取到func_name方法
            view_func = getattr(mod, func_name)
        except AttributeError:
            raise ViewDoesNotExist(
                "Could not import '%s'. View does not exist in module %s." %
                (lookup_view, mod_name)
            )

        # 成功获取func_name后, 判断是否是可调用对象
        else:
            # 如果非可调用, 抛出异常
            if not callable(view_func):
                raise ViewDoesNotExist(
                    "Could not import '%s.%s'. View is not callable." %
                    (mod_name, func_name)
                )

            # 可调用, 将视图函数引用返回
            return view_func


def get_mod_func(callback):
    # Convert 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    # 将字符串 'django.views.news.sotries.story_detail'转换成
    # 列表['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot + 1:]
