from gluon import XML

def button(merchant_id="123456789012345",
           products=[dict(name="shoes",
                          quantity=1,
                          price=23.5,
                          currency='USD',
                          description="running shoes black")]):
    product_template = """
    <input name="item_name_%(k)s" type="hidden" value="%(name)s"/>
    <input name="item_description_%(k)s" type="hidden" value="%(description)s"/>
    <input name="item_quantity_%(k)s" type="hidden" value="%(quantity)s"/>
    <input name="item_price_%(k)s" type="hidden" value="%(price)s"/>
    <input name="item_currency_%(k)s" type="hidden" value="%(currency)s"/>
    """    
    list_products = ''
    for k,product in enumerate(products):
        product['k']=k
        list_products += product_template % product
    button = '<form action="https://checkout.google.com/api/checkout/v2/checkoutForm/Merchant/%s" id="BB_BuyButtonForm" method="post" name="BB_BuyButtonForm" target="_top">%s<input name="_charset_" type="hidden" value="utf-8"/><input alt="" src="https://checkout.google.com/buttons/buy.gif?merchant_id=%s&amp;w=117&amp;h=48&amp;style=white&amp;variant=text&amp;loc=en_US" type="image"/></form>' % (merchant_id, list_products, merchant_id)
    return XML(button)

    
