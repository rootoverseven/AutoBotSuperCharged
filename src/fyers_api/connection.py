from fyers_apiv3 import fyersModel

class FyersConnection:
    def __init__(self, client_id, access_token):
        self.fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token)

    def place_order(self, order_params):
        try:
            response = self.fyers.place_order(data=order_params)
            if response['s'] == 'ok':
                return response['id']
            else:
                raise Exception(f"Order placement failed: {response['message']}")
        except Exception as e:
            print(f"Error placing order: {str(e)}")
            return None

    def get_quotes(self, symbols):
        try:
            response = self.fyers.quotes(data={"symbols": ",".join(symbols)})
            if response['s'] == 'ok':
                return {quote['n']: quote['v'] for quote in response['d']}
            else:
                raise Exception(f"Failed to fetch quotes: {response['message']}")
        except Exception as e:
            print(f"Error fetching quotes: {str(e)}")
            return {}

    def get_funds(self):
        try:
            response = self.fyers.funds()
            if response['s'] == 'ok':
                return response['fund_limit'][0]
            else:
                raise Exception(f"Failed to fetch funds: {response['message']}")
        except Exception as e:
            print(f"Error fetching funds: {str(e)}")
            return {}

    def get_positions(self):
        try:
            response = self.fyers.positions()
            if response['s'] == 'ok':
                return response['netPositions']
            else:
                raise Exception(f"Failed to fetch positions: {response['message']}")
        except Exception as e:
            print(f"Error fetching positions: {str(e)}")
            return []