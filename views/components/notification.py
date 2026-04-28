from __future__ import annotations

import asyncio

import flet as ft

from views.theme import colors

_TYPE_STYLE: dict[str, tuple[str, str, str]] = {
    "success": (ft.Icons.CHECK_CIRCLE_ROUNDED, colors.MINT, colors.MINT_DARK),
    "error": (ft.Icons.CANCEL_ROUNDED, colors.CORAL, colors.CORAL_DARK),
    "warning": (ft.Icons.WARNING_ROUNDED, colors.WARNING, "#4A3D24"),
    "info": (ft.Icons.INFO_ROUNDED, colors.KLEIN_BLUE_SOFT, colors.KLEIN_BLUE_DARK),
}

_MAX_VISIBLE = 5


class Notification:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self._column = ft.Column(spacing=8, tight=True)
        self._wrapper = ft.Container(
            top=24,
            right=24,
            content=self._column,
        )
        page.overlay.append(self._wrapper)

    def show(self, message: str, type: str = "info") -> None:
        self.page.run_task(self._animate, message, type)

    async def _animate(self, message: str, type: str) -> None:
        icon_name, accent, bg = _TYPE_STYLE.get(type, _TYPE_STYLE["info"])

        card = ft.Container(
            width=340,
            border_radius=14,
            bgcolor=colors.SURFACE,
            border=ft.border.only(
                left=ft.BorderSide(4, accent),
                top=ft.BorderSide(1, colors.OUTLINE_SOFT),
                right=ft.BorderSide(1, colors.OUTLINE_SOFT),
                bottom=ft.BorderSide(1, colors.OUTLINE_SOFT),
            ),
            padding=ft.padding.only(left=14, top=14, right=16, bottom=14),
            opacity=0,
            animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT_CUBIC),
            shadow=ft.BoxShadow(
                blur_radius=24,
                spread_radius=-8,
                color="#66000000",
                offset=ft.Offset(0, 10),
            ),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        width=32,
                        height=32,
                        border_radius=10,
                        bgcolor=bg,
                        alignment=ft.Alignment(0, 0),
                        content=ft.Icon(icon_name, size=18, color=accent),
                    ),
                    ft.Text(
                        message,
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=colors.TEXT_PRIMARY,
                        expand=True,
                    ),
                ],
            ),
        )

        if len(self._column.controls) >= _MAX_VISIBLE:
            oldest = self._column.controls[0]
            oldest.opacity = 0
            oldest.update()
            await asyncio.sleep(0.3)
            self._column.controls.pop(0)

        self._column.controls.append(card)
        self._column.update()

        await asyncio.sleep(0.05)
        card.opacity = 1
        card.update()

        await asyncio.sleep(3)

        card.opacity = 0
        card.update()
        await asyncio.sleep(0.3)

        if card in self._column.controls:
            self._column.controls.remove(card)
            self._column.update()
