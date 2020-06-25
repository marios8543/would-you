from aiohttp import ClientSession
from os import getenv
from json import dumps

class InstagramException(Exception):
    pass

class InstagramUser:
    def __init__(self, res):
        self.user_id = res["node"]["id"]
        self.username = res["node"]["username"]
        self.name = res["node"]["full_name"]
        self.profile_pic = res["node"]["profile_pic_url"]

    def to_dict(self):
        return {
            "id": self.user_id,
            "username": self.username,
            "name": self.name,
            "profile_pic": self.profile_pic
        }

BASE_URL = "https://www.instagram.com"
FOLLOWERS_QUERY = "d04b0a864b4b54837c0d870b0e77e076"

class Instagram:
    def __init__(self):
        self.cookies={
            "ds_user_id": getenv("IG_USER_ID"),
            "sessionid": getenv("IG_SESSION_ID")
        }

    async def init(self):
        print("Instagram client initialized")
        self.web = ClientSession(cookies=self.cookies)

    async def _get_id_from_username(self, username):
        res = await self.web.get("{}/{}/?__a=1".format(BASE_URL, username))
        if res.status == 200:
            res = await res.json()
            return res["graphql"]["user"]["id"]
        if res.status_code == 404:
            raise ValueError("User does not exist")
        else:
            raise InstagramException(await res.text())

    async def _get_following(self, user_id):
        following = []
        after = ""
        while True:
            res = await self.web.get("{}/graphql/query".format(BASE_URL), params={
                "query_hash": FOLLOWERS_QUERY,
                "variables": dumps({
                    "id": user_id,
                    "first": 50,
                    "fetch_mutual": False,
                    "after": after
                })
            })
            if res.status == 200:
                res = await res.json()
                for i in res["data"]["user"]["edge_follow"]["edges"]:
                    following.append(InstagramUser(i))
                if res["data"]["user"]["edge_follow"]["page_info"]["has_next_page"]:
                    after = res["data"]["user"]["edge_follow"]["page_info"]["end_cursor"]
                else:
                    break
            else:
                raise InstagramException(res.text)
        return following


    async def get_following(self, username):
        return await self._get_following(await self._get_id_from_username(username))