from __future__ import annotations
from pathlib import Path
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, Tuple, TypeVar, cast
from fastapi import Request, Response, Depends
from fastapi.templating import Jinja2Templates
from inspect import Parameter, Signature, get_annotations, iscoroutinefunction, signature

from algobattle_web.models import User
from algobattle_web.dependencies import curr_user

templates = Jinja2Templates(directory=Path(__file__).parent)
templates.env.policies |= {
    "json.dumps_kwargs": {
        "ensure_ascii": False,
        "sort_keys": False,
    },
}

P = ParamSpec("P")
R = ParamSpec("R")
S = TypeVar("S")

RetType = Tuple[str, dict[str, Any]] | str

def templated(fn: Callable[P, Awaitable[RetType] | RetType]) -> Callable[Concatenate[Request, User, P], Response | Awaitable[Response]]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the tournament of the template."""
    if iscoroutinefunction(fn):
        return templated_async(fn)
    else:
        return templated_sync(cast(Callable[P, RetType], fn))

def templated_async(fn: Callable[P, Awaitable[Tuple[str, dict[str, Any]] | str]]) -> Callable[Concatenate[Request, User, P], Awaitable[Response]]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the tournament of the template."""
    async def inner(request: Request, user: User, *args: P.args, **kwargs: P.kwargs) -> Response:
        if "request" in orig_params:
            kwargs["request"] = request
        if "user" in orig_params:
            kwargs["user"] = user
        ret = await fn(*args, **kwargs)
        return _make_template(request, user, ret)

    fixed_inner, orig_params = _fix_signature(inner, fn)
    return fixed_inner

def templated_sync(fn: Callable[P, Tuple[str, dict[str, Any]] | str]) -> Callable[Concatenate[Request, User, P], Response]:
    """Adds the `request: Request` and `user: User = Depends(curr_user)` parameters and passes them to the tournament of the template."""
    def inner(request: Request, user: User, *args: P.args, **kwargs: P.kwargs) -> Response:
        if "request" in orig_params:
            kwargs["request"] = request
        if "user" in orig_params:
            kwargs["user"] = user
        ret = fn(*args, **kwargs)
        return _make_template(request, user, ret)

    fixed_inner, orig_params = _fix_signature(inner, fn)
    return fixed_inner

def _make_template(request: Request, user: User, ret: Tuple[str, dict[str, Any]] | str) -> Response:
    if isinstance(ret, tuple):
        template_file, tournament = ret
    else:
        template_file, tournament = ret, {}

    new_tournament: dict[str, Any] = {"request": request, "user": user.encode()}
    return templates.TemplateResponse(template_file, new_tournament | tournament)

def _fix_signature(inner: Callable[P, S], fn: Callable[R, Any]) -> Tuple[Callable[P, S], set[str]]:
    # we need to get the annotations as actual objects and not strings,
    # get_annotations will eval all annotated ones but misses args that aren't annotated
    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name], kind=Parameter.KEYWORD_ONLY) for p in signature(fn).parameters.values()]

    # add new parameters if they aren't already present
    new_parameters = []
    orig_params = set()
    if "request" not in annotations:
        new_parameters.append(Parameter("request", Parameter.KEYWORD_ONLY, annotation=Request))
    else:
        orig_params.add("request")
    new_parameters.extend(parameters)
    if "user" not in annotations:
        new_parameters.append(Parameter("user", Parameter.KEYWORD_ONLY, annotation=User, default=Depends(curr_user)))
    else:
        orig_params.add("user")
    inner.__signature__ = Signature(
        parameters = new_parameters,
        return_annotation = signature(inner).return_annotation,
    )
    inner.__annotations__ = {"request": Request, "user": User, **inner.__annotations__}
    inner.__annotations__["return"] = Response

    return inner, orig_params



