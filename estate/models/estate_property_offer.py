from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Property Offer"
    _order = "price desc"

    _sql_constraints = [
        ("check_price", "CHECK (price > 0)",
         "The price must be positive")
    ]

    price = fields.Float()
    status = fields.Selection(selection=[("accepted", _("Accepted")),
                                         ("refused", _("Refused"))],
                              copy=False)
    date_deadline = fields.Date("Deadline", compute="_compute_date_deadline",
                                inverse="_inverse_date_deadline", store=True)
    validity = fields.Integer("Validity (days)", default=7)
    partner_id = fields.Many2one("res.partner", required=True)
    property_id = fields.Many2one("estate.property", string="Offer", index=True,
                                  required=True, )
    property_type_id = fields.Many2one(related="property_id.property_type_id")

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:
                record.date_deadline = record.create_date.date() \
                                       + relativedelta(days=record.validity | 7)
            else:
                # Workaround for creation of new offers
                record.date_deadline = fields.Date.today() \
                                       + relativedelta(days=record.validity | 7)

    def _inverse_date_deadline(self):
        for record in self:
            record.validity = (record.date_deadline
                               - record.create_date.date()).days

    def action_accept_offer(self):
        for record in self:
            if "accepted" in [record.status for record in
                              record.property_id.offer_ids]:
                raise UserError(_("Another offer has already been accepted."))
            else:
                for offer in self:
                    offer.status = "accepted"
                    offer.property_id.selling_price = offer.price
                    offer.property_id.buyer_id = offer.partner_id
                    offer.property_id.state = "offer_accepted"
            return True

    def action_refuse_offer(self):
        for record in self:
            if record.status == "accepted":
                record.property_id.buyer_id = None
                record.property_id.selling_price = None
            record.status = "refused"
            record.property_id.state = "offer_received"
        return True

    @api.model
    def create(self, vals):
        offer = super(EstatePropertyOffer, self).create(vals)
        offer.property_id.state = 'offer_received'
        max_offer = max([_offer.price for _offer in
                        offer.property_id.offer_ids])
        if offer.price < max_offer:
            txt = "The offer must be atleast {:.2f}"
            raise UserError(txt.format(max_offer))
        return offer
