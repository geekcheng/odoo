# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class StockMoveInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.ProductProduct = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.AccountJournal = cls.env['account.journal']

        cls.partner_18 = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.pricelist_id = cls.env.ref('product.list0')
        cls.product_11 = cls.env['product.product'].create({'name': 'A product to deliver'})
        cls.product_cable_management_box = cls.env['product.product'].create({
            'name': 'Another product to deliver',
            'weight': 1.0,
            'invoice_policy': 'order',
        })
        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_delivery_normal = cls.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.normal_delivery = cls.env['delivery.carrier'].create({
            'name': 'Normal Delivery Charges',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery_normal.id,
        })

    def test_01_delivery_stock_move(self):
        # Test if the stored fields of stock moves are computed with invoice before delivery flow
        self.product_11.write({
            'weight': 0.25,
        })

        self.sale_prepaid = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist_id.id,
            'order_line': [(0, 0, {
                'name': 'Cable Management Box',
                'product_id': self.product_cable_management_box.id,
                'product_uom_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_prepaid.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I confirm the SO.
        self.sale_prepaid.action_confirm()
        self.sale_prepaid._create_invoices()

        # I check that the invoice was created
        self.assertEqual(len(self.sale_prepaid.invoice_ids), 1, "Invoice not created.")

        # I confirm the invoice

        self.invoice = self.sale_prepaid.invoice_ids
        self.invoice.action_post()

        # I pay the invoice.
        self.journal = self.AccountJournal.search([('type', '=', 'cash'), ('company_id', '=', self.sale_prepaid.company_id.id)], limit=1)

        register_payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=self.invoice.ids).create({
            'journal_id': self.journal.id,
        })
        register_payments._create_payments()

        # Check the SO after paying the invoice
        self.assertNotEqual(self.sale_prepaid.invoice_count, 0, 'order not invoiced')
        self.assertTrue(self.sale_prepaid.invoice_status == 'invoiced', 'order is not invoiced')
        self.assertEqual(len(self.sale_prepaid.picking_ids), 1, 'pickings not generated')

        # Check the stock moves
        moves = self.sale_prepaid.picking_ids.move_ids
        self.assertEqual(moves[0].product_qty, 2, 'wrong product_qty')
        self.assertEqual(moves[0].weight, 2.0, 'wrong move weight')

        # Ship
        self.picking = self.sale_prepaid.picking_ids._action_done()
