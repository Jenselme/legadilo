from typing import TypeAlias

FormChoice: TypeAlias = tuple[str, str]  # noqa: UP040 use the type keyword (mypy doesn't support it)
FormChoices: TypeAlias = list[FormChoice]  # noqa: UP040 use the type keyword (mypy doesn't support it)
