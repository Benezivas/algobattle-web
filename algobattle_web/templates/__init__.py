from __future__ import annotations
from pathlib import Path
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, Tuple
from fastapi import Request, Response
from fastapi.templating import Jinja2Templates
from inspect import Parameter, Signature, get_annotations, signature

templates = Jinja2Templates(directory=Path(__file__).parent)


P = ParamSpec("P")
def templated(fn: Callable[P, Awaitable[Tuple[str, dict[str, Any]] | str]]) -> Callable[Concatenate[Request, P], Awaitable[Response]]:
    async def inner(request: Request, *args: P.args, **kwargs: P.kwargs):
        ret = await fn(*args, **kwargs)
        if isinstance(ret, tuple):
            template_file, context = ret
        else:
            template_file, context = ret, {}
        return templates.TemplateResponse(template_file, {"request": request} | context)

    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]
    inner.__signature__ = Signature(
        parameters = [
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            *parameters,
        ],
        return_annotation = signature(inner).return_annotation,
    )

    return inner

def templated_sync(fn: Callable[P, Tuple[str, dict[str, Any]] | str]) -> Callable[Concatenate[Request, P], Response]:
    def inner(request: Request, *args: P.args, **kwargs: P.kwargs):
        ret = fn(*args, **kwargs)
        if isinstance(ret, tuple):
            template_file, context = ret
        else:
            template_file, context = ret, {}
        return templates.TemplateResponse(template_file, {"request": request} | context)

    annotations = {n: Parameter.empty for n in signature(fn).parameters} | get_annotations(fn, eval_str=True)
    parameters = [p.replace(annotation=annotations[p.name]) for p in signature(fn).parameters.values()]
    inner.__signature__ = Signature(
        parameters = [
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request),
            *parameters,
        ],
        return_annotation = signature(inner).return_annotation,
    )

    return inner

