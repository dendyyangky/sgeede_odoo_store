/** @odoo-module **/

import { Component, markup, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AnnouncementBanner extends Component {
    static template = "sgeede_company_announcement.AnnouncementBanner";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.dismissedIds = new Set();
        this.state = useState({
            announcements: [],
            showInHomeMenu: false,
        });

        onMounted(() => {
            this.updateHomeMenuVisibility();
            this.homeMenuObserver = new MutationObserver(() => this.updateHomeMenuVisibility());
            this.homeMenuObserver.observe(document.body, {
                attributes: true,
                attributeFilter: ["class"],
                childList: true,
                subtree: true,
            });
        });

        onWillUnmount(() => {
            this.homeMenuObserver?.disconnect();
        });
    }

    isHomeMenuVisible() {
        return (
            document.body.classList.contains("o_home_menu_background") ||
            Boolean(document.querySelector(".o_home_menu"))
        );
    }

    async loadAnnouncements() {
        const announcements = await this.orm.call(
            "company.announcement",
            "get_active_announcements",
            []
        );
        this.state.announcements = announcements
            .filter((a) => !this.dismissedIds.has(a.id))
            .map((a) => ({
                ...a,
                message: markup(a.message || ""),
            }));
    }

    updateHomeMenuVisibility() {
        const wasVisible = this.state.showInHomeMenu;
        this.state.showInHomeMenu = this.isHomeMenuVisible();
        if (!wasVisible && this.state.showInHomeMenu) {
            this.loadAnnouncements();
        }
    }

    async dismiss(announcement) {
        this.dismissedIds.add(announcement.id);
        this.state.announcements = this.state.announcements.filter(
            (item) => item.id !== announcement.id
        );
        await this.orm.call("company.announcement", "dismiss_announcement", [announcement.id]);
    }
}

registry.category("main_components").add("sgeede_company_announcement.AnnouncementBanner", {
    Component: AnnouncementBanner,
});