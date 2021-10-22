from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "Estate Property"
    _order = "id desc"

    _sql_constraints = [
        ("expected_price", "CHECK (expected_price > 0)",
         "The expected price must be strictly positive"),
        ("selling_price", "CHECK (selling_price >= 0)",
         "The selling price must be positive")
    ]

    name = fields.Char("Title", required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(
        "Available From",
        default=fields.Date.today() + relativedelta(months=3),
        copy=False
    )
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer("Living Area (sqm)")
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer()
    garden_orientation = fields.Selection(
        string="Garden Orientation",
        selection=[("north", _("North")),
                   ("south", _("South")),
                   ("east", _("East")),
                   ("west", _("West")),
                   ]
    )
    state = fields.Selection(
        string="Status",
        selection=[("new", _("New")),
                   ("offer_received", _("Offer Received")),
                   ("offer_accepted", _("Offer Accepted")),
                   ("sold", _("Sold")),
                   ("canceled", _("Canceled"))
                   ],
        default="new",
        required=True,
        copy=False
    )
    active = fields.Boolean(default=True)
    property_type_id = fields.Many2one("estate.property.type")
    total_area = fields.Integer("Total Area (sqm)",
                                compute="_compute_total_area")
    best_offer = fields.Float(compute="_compute_best_offer")
    salesman_id = fields.Many2one("res.users",
                                  default=lambda self: self.env.user)
    buyer_id = fields.Many2one("res.partner", copy=False)
    tag_ids = fields.Many2many("estate.property.tag")
    offer_ids = fields.One2many("estate.property.offer", "property_id",
                                string="Offers")

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    @api.depends("offer_ids")
    def _compute_best_offer(self):
        for record in self:
            if record.offer_ids:
                record.best_offer = max(record.offer_ids.mapped("price"))
            else:
                record.best_offer = None

    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = None
            self.garden_orientation = None

    def action_sold_property(self):
        for record in self:
            if record.state != "canceled":
                record.state = "sold"
            else:
                raise UserError(_("Canceled properties cannot be sold."))
        return True

    def action_cancel_property(self):
        for record in self:
            if record.state != "sold":
                record.state = "canceled"
                for offer in record.offer_ids:
                    offer.unlink()
            else:
                raise UserError(_("Sold properties cannot be canceled."))
        return True

    def action_restore_property(self):
        for record in self:
            if record.state == "canceled":
                record.state = "new"
            else:
                raise UserError(_("Only canceled properties can be restored."))
        return True

    @api.constrains("selling_price")
    def _check_percent(self):
        for record in self:
            if not float_is_zero(record.selling_price, 0) \
                    and float_compare(record.selling_price
                                      / record.expected_price, 0.9,
                                      precision_digits=2) == -1:
                raise ValidationError("The selling price must be atleast 90% of"
                                      " the expected price! You must reduce"
                                      " the expected price if you want to"
                                      " accept this offer.")

    @api.ondelete(at_uninstall=False)
    def _unlink(self):
        if self.state not in ['new', 'canceled']:
            raise UserError("Only new or canceled properties can be deleted")
