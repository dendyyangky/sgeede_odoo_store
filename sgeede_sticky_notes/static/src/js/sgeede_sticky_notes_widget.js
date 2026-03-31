/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class SGEEDEStickyNotesWidget extends Component {
    static template = "sgeede_sticky_notes.StickyNotes";
    static props = ["*"]

    setup(){
        this.orm = useService("orm")
        this.state = useState({
            collapsed: false,
            adding: false,
            newContent: "",
            newColor: "yellow"
        });
    }

    getUserName(userId) {
        if (!userId) return '';
        
        if (Array.isArray(userId) || userId[1] !== undefined) {
            return userId[1];
        }
        
        if (userId.display_name !== undefined) {
            return userId.display_name;
        }

        return '';
    }

    get notes() {
        const field = this.props.record.data[this.props.name];
        if (!field || !field.records) return [];
        console.log("note data:", field.records.map(r => r.data));
        return field.records;
    }

    
    async reloadRecord() {
        try {
            await this.props.record.load();
        } catch {
            await this.props.record.load({ fieldNames: [this.props.name] });
        }
    }
    
    async archiveNote(noteId) {
        await this.orm.write("sgeede.sticky.notes", [noteId], { active: false });
        this.reloadRecord()
    }

    formatDate(dateVal) {
        if (!dateVal) return '';
        const str = dateVal.toString();
        return str.slice(0, 10); 
    }
    
    get parentField() {
        const modelMap = {
            'sale.order':'sale_order_id',
            'purchase.order': 'purchase_order_id',
            'account.move': 'account_move_id',
        };
        return modelMap[this.props.record.resModel] || null;
    }

    async saveNote() {
        if (!this.state.newContent.trim()) return;

        const field = this.parentField;
        if (!field) {
            console.error(`Sticky notes: unsupported model "${this.props.record.resModel}"`);
            return;
        }

        await this.orm.create("sgeede.sticky.notes", [{
            [field]: this.props.record.resId,
            content: this.state.newContent,
            color: this.state.newColor,
        }]);

        this.state.newContent = "";
        this.state.newColor = "yellow";
        this.state.adding = false;
        this.reloadRecord()
    }


    toggleCollapse() {
        this.state.collapsed = !this.state.collapsed;
    }

}

registry.category("fields").add("sticky_notes_widget", {
    component: SGEEDEStickyNotesWidget,
    supportedTypes: ["one2many"],
})