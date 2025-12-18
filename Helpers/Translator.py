import logging
import traceback

import aiohttp


async def TranslateText(source, target, text, token):
    try:
        print(text)
        async with aiohttp.ClientSession() as session:
            data = {
          "sourceLanguageCode": source,
          "targetLanguageCode": target,
          "format": "HTML",
          "texts": [
            text
          ],
          "folderId": "b1gdch5lr1n6rvu5o1pa",
          "speller": "true"
        }
            r = await session.post(url="https://translate.api.cloud.yandex.net/translate/v2/translate", json=data, headers={"Authorization": f"Bearer {token}"})
            response = await r.json()

            translate = response['translations'][0]['text']
            return translate
    except Exception as e:
        logging.error(f"Error in TranslateText: {traceback.format_exc()}")
        logging.error("API Response: " + str(response))
        return text