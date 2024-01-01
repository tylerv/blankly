"""
    Class for defining headers for deployment infrastructure
    Copyright (C) 2021  Emerson Dove

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import smtplib
import ssl

from typing import Any

from blankly.utils.utils import load_notify_preferences
from blankly.frameworks.strategy import Strategy
from blankly.frameworks.screener.screener import Screener
from blankly.exchanges.interfaces.paper_trade.backtest_result import BacktestResult


class Reporter:
    def __init__(self):
        self.__live_vars = {}
        self.__screener = None
        pass

    def export_live_var(self, var: Any, name: str, description: str = None):
        """
        Create a variable that can be updated by external processes
        All strings must be in ascii characters

        Args:
            var: Any variable that can represented in a string (ex: float, str, int)
            name: The name of the live_var
            description (optional): A longer description for use in GUIs or other areas where context is important
        """
        self.__live_vars[id(var)] = var

    def update_live_var(self, var):
        """
        Get the variable as with any changes that may have occurred

        Args:
            var: The variable that was exported initially
        """
        return self.__live_vars[id(var)]

    def export_strategy(self, strategy: Strategy):
        """
        Export a strategy for monitoring. This is used internally on the construction of the strategy object

        Args:
            strategy (Strategy): The strategy object to monitor
        """
        pass

    def export_screener(self, screener: Screener):
        """
        Export a screener object to the backend for monitoring

        Args:
            screener: A screener object to export
        """
        if self.__screener is None:
            self.__screener = screener
        else:
            raise RuntimeError("Currently only a single screener can be created per model.")

    def export_screener_result(self, screener: Screener):
        """
        Re-export for the finished screener result

        Args:
            screener: A screener object to export
        """
        pass

    def export_backtest_result(self, platform_result: dict):
        """
        Re-export for the finished screener result

        Args:
            platform_result: A blankly backtest result object
        """
        pass

    def export_used_exchange(self, exchange_name):
        """
        Export the string identifier for a used exchange
        """
        pass

    def log_market_order(self, exchange_out: dict, exchange_type: str):
        """
        Log a market order
        """
        pass

    def log_limit_order(self, exchange_out: dict, exchange_type: str):
        """
        Log a limit order
        """
        pass

    def update_order(self, exchange_out: dict, exchange_type: str):
        """
        Update an existing order
        """
        pass

    def export_used_symbol(self, symbol):
        """
        Export the currency name for a used currency
        """
        pass

    def annotate_order(self, order_id, annotation):
        """
        Update the annotation on an existing order
        """
        pass

    def text(self, text: str):
        """
        Send a text message to the number if notify.json OR the phone number attached to your account if the model
        is deployed live

        Args:
            text: The message body to be sent to your phone number
        """
        notify_preferences = load_notify_preferences()
        provider = notify_preferences['text']['provider']
        phone_number = notify_preferences['text']['phone_number']

        email_lookup = {
            'att': '@txt.att.net',
            'boost': '@smsmyboostmobile.com',
            'cricket': '@sms.cricketwireless.net',
            'sprint': '@messaging.sprintpcs.com',
            't_mobile': '@tmomail.net',
            'us_cellular': '@email.uscc.net',
            'verizon': '@vtext.com',
            'virgin_mobile': '@vmobl.com'
        }
        try:
            email = email_lookup[provider]
        except KeyError:
            raise KeyError("Provider not found. Check the notify.json documentation to see supported providers.")

        self.__send_email(text, override_receiver=phone_number + email)

    @staticmethod
    def __send_email(email_str: str, override_receiver=None):
        """
        Internal email send. This is separated because override_receiver shouldn't be exposed to the user
        """
        notify_preferences = load_notify_preferences()
        port = notify_preferences['email']['port']
        smtp_server = notify_preferences['email']['smtp_server']
        sender_email = notify_preferences['email']['sender_email']
        receiver_email = notify_preferences['email']['receiver_email']
        password = notify_preferences['email']['password']

        if override_receiver is not None:
            receiver_email = override_receiver

        message = email_str

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    def email(self, email: str):
        """
        Send an email to the email specified in the notify.json OR your user account email if run live

        Args:
            email: The body of the email to send
        """
        self.__send_email(email)
        
    def chat(self, message: Any, header = 'Message from Blankly'):
        """
        Sends a text message to a Google Chat Space through a webhook_url
        Create the webhook following these instructions:
            https://developers.google.com/chat/how-tos/webhooks#register_the_incoming_webhook
            Register the incoming webhook
            1. In a browser, open Chat. Webhooks aren't configurable from the Chat mobile app.
            2. Go to the space where you want to add a webhook.
            3. Next to the space title, click the expand more arrow, and then click Apps & integrations.
            4. Click Add webhooks.
            5. In the Name field, enter a name for your webhook (such as "Blankly Notifications").
            6. In the Avatar URL field, enter a URL to an icon (such as https://blankly.finance/_nuxt/img/blankly-black.c8ffff6.svg).
            7. Click Save.
            8. To copy the webhook URL, click more_vert More, and then click Copy link.
        Args:
            message: The text of the message to send to the webhook_url specified in notify.json
                message can be a plaintext string, or a dict of values to create a card from.
            header: The header of the message to send in the card. Ignored if message is plaintext.
        """
        # https://github.com/googleworkspace/google-chat-samples/blob/main/python/webhook/quickstart.py
        from json import dumps
        from httplib2 import Http
    
        try:
            notify_preferences = load_notify_preferences()
            webhook = notify_preferences['chat']['webhook_url']
    
            if (
                isinstance(message, dict)
                or isinstance(message, pd.DataFrame)
                or isinstance(message, list)
                or isinstance(message, tuple)
            ):
                app_message = self.__create_card(header, message)
            else:
                # assume plain_text
                app_message = {"text": message}
            message_headers = {"Content-Type": "application/json; charset=UTF-8"}
            http_obj = Http()
            body = dumps(app_message)
            response = http_obj.request(
                uri=webhook,
                method="POST",
                headers=message_headers,
                body=body,
            )
            # print(response)
        except KeyError:
            raise KeyError("Google Chat webhook URL not found. Check the notify.json documentation")

    @staticmethod
    def __create_card(header: str, data: Any) -> dict:
        """
        Builds a Card to send a dictionary to a google chat in a table-like format.
        
        Handles several types of data structures, but does NOT currently handle nested structures.
        Best to send a simple dict, list, tuple, or str.
        """
        sections = []
        
        def get_df_section(df: pd.DataFrame, text: str = None):
            cols = df.columns.tolist()
            items = [{"title": str(item), "textAlignment": "CENTER"} for item in cols]
            items += [{"title": str(cell_data), "textAlignment": "START"} for cell_data in
                      df.values.ravel()]
            result = {
                "collapsible": True,
                "uncollapsibleWidgetsCount": 1,
                "widgets": []
            }
            if text:
                result['widgets'].append({"textParagraph": {"text": str(text)}})
        
            result['widgets'].append(
                {
                    "grid": {
                        "columnCount": df.shape[1],  # Number of Columns in df
                        "items": items
                    }
                }
            )
        
            return result
        
        if isinstance(data, pd.DataFrame):
            result = get_df_section(data)
        elif isinstance(data, dict):
            result = {
                "collapsible": True,
                "uncollapsibleWidgetsCount": 1,
                "widgets": [
                    {
                        "grid": {
                            "columnCount": 2,  # Number of Columns (key & value)
                            "items": [],
                        }
                    }
                ]
            }
            for inner_key, inner_value in data.items():
                result['widgets'][0]['grid']['items'] += [
                    {"title": str(inner_key), "textAlignment": "START"},
                    {"title": str(inner_value), "textAlignment": "START"}
                ]
        elif isinstance(data, list):
            result = {
                "collapsible": True,
                "uncollapsibleWidgetsCount": 1,
                "widgets": [
                    {"textParagraph": {"text": str(item)}} for item in data
                ]
            }
        elif isinstance(data, tuple):
            result = {
                "collapsible": False,
                "widgets": [
                    {
                        "grid": {
                            "columnCount": len(data),  # Number of items in Tuple
                            "items": [{"title": str(item), "textAlignment": "START"} for item in data]
                        }
                    }
                ]
            }
        else:
            # Assume simple data type.
            result = {
                "collapsible": False,
                "widgets": [
                    {"textParagraph": {"text": str(data)}}
                ]
            }
        
        sections.append(result)
        
        return {
            "cardsV2": [
                {
                    "cardId": "resultCard",
                    "card": {
                        'header': {
                            "title": header
                        },
                        "sections": sections
                    },
                }
            ]
        }
