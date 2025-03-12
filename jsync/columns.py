from typing import Optional

from rich.progress import (
    Column,
    Highlighter,
    JustifyMethod,
    ProgressColumn,
    StyleType,
    Task,
    Text,
)


class FlexiColumn(ProgressColumn):
    """A column containing Download Rate"""

    def __init__(
        self,
        func: callable,
        style: StyleType = "none",
        justify: JustifyMethod = "left",
        markup: bool = True,
        highlighter: Optional[Highlighter] = None,
        table_column: Optional[Column] = None,
    ) -> None:
        self.func = func
        self.justify: JustifyMethod = justify
        self.style = style
        self.markup = markup
        self.highlighter = highlighter
        super().__init__()

    def render(self, task: "Task") -> Text:
        _text = self.func(task)

        if self.markup:
            text = Text.from_markup(_text, style=self.style, justify=self.justify)
        else:
            text = Text(_text, style=self.style, justify=self.justify)

        if self.highlighter:
            self.highlighter.highlight(text)

        return text
