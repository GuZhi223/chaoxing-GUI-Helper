from __future__ import annotations

import flet as ft

from models.account import AccountConfig
from viewmodels.account_viewmodel import AccountCardState, AccountViewModel
from views.components.account_card import AccountCard
from views.components.account_dialog import AccountDialog
from views.theme import colors


class AccountPage(ft.Container):
    def __init__(self, vm: AccountViewModel) -> None:
        super().__init__()
        self.vm = vm
        self.vm.on_change = self.refresh
        self.expand = True
        self.card_list = ft.ListView(expand=True, spacing=12, padding=ft.padding.only(right=4))
        self._card_controls: dict[str, AccountCard] = {}
        self.content = self._build()
        self.refresh()

    def _build(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=18,
            controls=[
                self._toolbar(),
                ft.Container(
                    expand=True,
                    border_radius=18,
                    bgcolor=colors.SURFACE_LOW,
                    border=ft.border.all(1, colors.OUTLINE_SOFT),
                    padding=18,
                    shadow=ft.BoxShadow(
                        blur_radius=32,
                        spread_radius=-8,
                        color="#66000000",
                        offset=ft.Offset(0, 18),
                    ),
                    content=self.card_list,
                ),
            ],
        )

    def _toolbar(self) -> ft.Control:
        add_button = ft.Container(
            height=44,
            border_radius=14,
            bgcolor=colors.KLEIN_BLUE,
            padding=ft.padding.symmetric(horizontal=18),
            ink=True,
            animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            on_click=self._open_add_dialog,
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.ADD_ROUNDED, size=21, color=colors.TEXT_PRIMARY),
                    ft.Text(
                        "添加新账号",
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=colors.TEXT_PRIMARY,
                    ),
                ],
            ),
        )

        def hover(event: ft.HoverEvent) -> None:
            add_button.bgcolor = colors.KLEIN_BLUE_SOFT if event.data == "true" else colors.KLEIN_BLUE
            add_button.scale = 1.02 if event.data == "true" else 1
            add_button.update()

        add_button.on_hover = hover

        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    spacing=4,
                    controls=[
                        ft.Text(
                            "账号运行",
                            size=30,
                            weight=ft.FontWeight.W_700,
                            color=colors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "管理多账号任务、视频进度与运行状态。",
                            size=14,
                            color=colors.TEXT_MUTED,
                        ),
                    ],
                ),
                add_button,
            ],
        )

    def refresh(self) -> None:
        active_ids = {card.account_id for card in self.vm.cards}
        for account_id in list(self._card_controls):
            if account_id not in active_ids:
                del self._card_controls[account_id]

        controls: list[ft.Control] = []
        for index, card in enumerate(self.vm.cards):
            control = self._card_controls.get(card.account_id)
            if control is None:
                control = AccountCard(
                    state=card,
                    on_edit=self._open_edit_dialog,
                    on_start=self.vm.start_account,
                    on_stop=self.vm.stop_account,
                    on_delete=self.vm.remove_account,
                    reveal_delay_ms=index * 45,
                )
                self._card_controls[card.account_id] = control
            else:
                control.refresh_state(card)
            controls.append(control)

        self.card_list.controls = controls
        if self._is_mounted():
            self.update()

    def _open_add_dialog(self, _: ft.ControlEvent | None = None) -> None:
        dialog = AccountDialog(
            on_save=self._save_new_account,
            on_fetch_courses=self.vm.fetch_courses,
            title="添加账号",
        )
        self._show_dialog(dialog)

    def _open_edit_dialog(self, account: AccountCardState) -> None:
        self.vm.open_config(account.account_id)
        dialog = AccountDialog(
            account=account,
            title="编辑账号",
            on_save=lambda config: self.vm.update_account(account.account_id, config),
            on_fetch_courses=self.vm.fetch_courses,
        )
        self._show_dialog(dialog)

    def _save_new_account(self, config: AccountConfig) -> None:
        self.vm.add_account(config)

    def _show_dialog(self, dialog: AccountDialog) -> None:
        page = self._page_or_none()
        if page is None:
            return

        dialog_instance = dialog.build()
        if dialog_instance not in page.overlay:
            page.overlay.append(dialog_instance)

        dialog_instance.open = True
        page.update()
        dialog_instance.update()

    def _is_mounted(self) -> bool:
        return self._page_or_none() is not None

    def _page_or_none(self) -> ft.Page | None:
        try:
            return self.page
        except RuntimeError:
            return None
