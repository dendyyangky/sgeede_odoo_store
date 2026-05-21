from odoo import Command, api, fields, models

class CompanyAnnouncement(models.Model):
    _name = "company.announcement"
    _description = "Company Announcement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, start_datetime desc, id desc"

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("published", "Published"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    level = fields.Selection(
        [
            ("info", "Information"),
            ("success", "Good News"),
            ("warning", "Attention"),
            ("danger", "Critical"),
        ],
        default="info",
        required=True,
    )
    message = fields.Html(required=True, sanitize=True)
    start_datetime = fields.Datetime(string="Start Date")
    end_datetime = fields.Datetime(string="End Date")
    company_ids = fields.Many2many(
        "res.company",
        string="Companies",
        help="Leave empty to show the announcement in every company.",
    )
    dismissed_user_ids = fields.Many2many(
        "res.users",
        "company_announcement_dismissed_user_rel",
        "announcement_id",
        "user_id",
        string="Dismissed By",
        readonly=True,
        copy=False,
    )
    is_visible = fields.Boolean(compute="_compute_is_visible", search="_search_is_visible")

    @api.depends("state", "start_datetime", "end_datetime")
    def _compute_is_visible(self):
        now = fields.Datetime.now()
        for announcement in self:
            announcement.is_visible = (
                announcement.state == "published"
                and (not announcement.start_datetime or announcement.start_datetime <= now)
                and (not announcement.end_datetime or announcement.end_datetime >= now)
            )

    def _search_is_visible(self, operator, value):
        now = fields.Datetime.now()
        visible_domain = ([
            ("state", "=", "published"),
            "|",
            ("start_datetime", "=", False),
            ("start_datetime", "<=", now),
            "|",
            ("end_datetime", "=", False),
            ("end_datetime", ">=", now),
        ])
        if (operator, value) in [("=", True), ("!=", False)]:
            return visible_domain
        return ~visible_domain

    def action_publish(self):
        self.write({"state": "published"})

    def action_unpublish(self):
        self.write({"state": "draft"})

    @api.model
    def get_active_announcements(self):
        user = self.env.user
        now = fields.Datetime.now()
        domain = [
            ("state", "=", "published"),
            "|", ("start_datetime", "=", False), ("start_datetime", "<=", now),
            "|", ("end_datetime", "=", False), ("end_datetime", ">=", now),
            ("dismissed_user_ids", "not in", [user.id]),
            "|", ("company_ids", "=", False), ("company_ids", "in", [self.env.company.id]),
        ]
        announcements = self.search(domain)
        return [
            {
                "id": announcement.id,
                "title": announcement.name,
                "message": announcement.message,
                "level": announcement.level,
            }
            for announcement in announcements
        ]

    @api.model
    def dismiss_announcement(self, announcement_id):
        user = self.env.user
        announcement = self.browse(announcement_id)
        if announcement.exists():
            announcement.sudo().write({
                "dismissed_user_ids": [Command.link(user.id)]
            })
        return True