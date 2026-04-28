from __future__ import annotations

from abc import ABC, abstractmethod

from .models import ParseRequest, ParsedDocument


class BaseParser(ABC):
    name = "base"

    @abstractmethod
    def supports(self, request: ParseRequest) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, request: ParseRequest) -> ParsedDocument:
        raise NotImplementedError
