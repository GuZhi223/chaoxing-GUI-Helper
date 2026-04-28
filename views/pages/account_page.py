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
        self._select_all_cb = ft.Checkbox(
            value=False,
            active_color=colors.KLEIN_BLUE,
            check_color=colors.TEXT_PRIMARY,
            on_change=self._on_select_all_changed,
        )
        self._selected_count_text = ft.Text(size=14, color=colors.TEXT_SECONDARY, weight=ft.FontWeight.W_600)
        self._batch_bar = self._build_batch_bar()
        self.content = self._build()
        self.refresh()

    def _build(self) -> ft.Control:
        return ft.Column(
            expand=True,
            spacing=18,
            controls=[
                self._toolbar(),
                self._batch_bar,
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
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._select_all_cb,
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
                    ],
                ),
                ft.Row(
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        self._selected_count_text,
                        add_button,
                    ],
                ),
            ],
        )

    def _build_batch_bar(self) -> ft.Control:
        def batch_icon_button(icon: str, label: str, color: str, on_click) -> ft.Container:
            btn = ft.Container(
                height=38,
                border_radius=12,
                bgcolor=colors.SURFACE_HIGH,
                padding=ft.padding.symmetric(horizontal=14),
                ink=True,
                animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
                on_click=on_click,
                content=ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, size=18, color=color),
                        ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=color),
                    ],
                ),
            )

            def hover(event: ft.HoverEvent) -> None:
                btn.bgcolor = colors.SURFACE_HIGHEST if event.data == "true" else colors.SURFACE_HIGH
                btn.scale = 1.03 if event.data == "true" else 1
                btn.update()

            btn.on_hover = hover
            return btn

        return ft.Container(
            visible=False,
            border_radius=14,
            bgcolor=colors.SURFACE,
            border=ft.border.all(1, colors.OUTLINE_SOFT),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            batch_icon_button(ft.Icons.PLAY_ARROW_ROUNDED, "批量启动", colors.MINT, self._on_batch_start),
                            batch_icon_button(ft.Icons.STOP_ROUNDED, "批量停止", colors.WARNING, self._on_batch_stop),
                            batch_icon_button(ft.Icons.DELETE_OUTLINE_ROUNDED, "批量删除", colors.CORAL, self._on_batch_delete),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            ft.Container(
                                height=38,
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=14),
                                ink=True,
                                animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
                                on_click=self._on_deselect_all,
                                bgcolor=colors.SURFACE_HIGH,
                                content=ft.Text("取消全选", size=13, weight=ft.FontWeight.W_600, color=colors.TEXT_SECONDARY),
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _on_select_all_changed(self, _: ft.ControlEvent) -> None:
        if len(self.vm.selected_accounts) == len(self.vm.cards) and len(self.vm.cards) > 0:
            self.vm.deselect_all()
        else:
            self.vm.select_all()

    def _on_batch_start(self, _: ft.ControlEvent) -> None:
        self.vm.batch_start()

    def _on_batch_stop(self, _: ft.ControlEvent) -> None:
        self.vm.batch_stop()

    def _on_batch_delete(self, _: ft.ControlEvent) -> None:
        self.vm.batch_delete()

    def _on_deselect_all(self, _: ft.ControlEvent | None = None) -> None:
        self.vm.deselect_all()

    def refresh(self) -> None:
        active_ids = {card.account_id for card in self.vm.cards}
        for account_id in list(self._card_controls):
            if account_id not in active_ids:
                del self._card_controls[account_id]

        selected = self.vm.selected_accounts
        count = len(selected)

        self._select_all_cb.value = count > 0 and count == len(self.vm.cards)
        self._select_all_cb.tristate = False
        self._selected_count_text.value = f"已选 {count} 项" if count > 0 else ""
        self._batch_bar.visible = count > 0

        controls: list[ft.Control] = []
        for index, card in enumerate(self.vm.cards):
            is_selected = card.account_id in selected
            control = self._card_controls.get(card.account_id)
            if control is None:
                control = AccountCard(
                    state=card,
                    on_edit=self._open_edit_dialog,
                    on_start=self.vm.start_account,
                    on_stop=self.vm.stop_account,
                    on_delete=self.vm.remove_account,
                    on_copy=self._copy_account,
                    on_toggle_select=self.vm.toggle_selection,
                    selected=is_selected,
                    reveal_delay_ms=index * 45,
                )
                self._card_controls[card.account_id] = control
            else:
                control.refresh_state(card, selected=is_selected)
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

    def _copy_account(self, account_id: str) -> None:
        self.vm.copy_account(account_id)

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
