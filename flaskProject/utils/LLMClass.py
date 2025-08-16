from zai import ZaiClient, ZhipuAiClient
import base64
from zai import ZhipuAiClient
import httpx

httpx_client = httpx.Client(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100
    ),
    timeout=30.0
)

client = ZhipuAiClient(
    api_key="9b9a02c889144edb8991cd32b958e777.Iz77dshWlHaViAJL",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    timeout=httpx.Timeout(timeout=300.0, connect=8.0),
    max_retries=3,
    http_client=httpx_client
)

class MyLLM:
    def encode_image(self,image_path):
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def parse_photo(self, url):
        base64_image = self.encode_image(url)
        response = client.chat.completions.create(
            model="glm-4v",
            messages=[
                {"role": "system",
                 "content": "你现在是一个资深的质检工程师,专门负责检查生产过程中各个材质的零件是否完好"},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请帮我分析该木制材料是否存在非环境的重大缺损。如有，请说出主要缺损情况,若缺陷情况比较轻微或自然原因，请回复几乎完好"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content

# llm = MyLLM()
# print(llm.parse_photo("D:\\\HuaweiMoveData\\Users\\Howard\\Desktop\\good.jpg"))
