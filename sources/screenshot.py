

findAllLinksv2= """(?:\"|')([\w]{2,10}:[\\\/]+[\w\d\*\_\-\.\:]+)?((([\\\/]+)([\.\w\d\_\-\:]+)((?![\.\w\d\_\-\:]+)[\\\/]+)?)+|(([\.\w\d\_\-\:]+)([\\\/]+)((?![\\\/]+)[\.\w\d\_\-\:]+)?)+)?(\?([\w\d\-\_\;{}()\[\]]+(\=([^&,\s]+(\&)?)?)?){0,})?(?:\"|')"""


import asyncio
from pyppeteer import launch

async def main():
    # launch chromium browser in the background
    browser = await launch()
    # open a new tab in the browser
    page = await browser.newPage()
    # add URL to a new page and then open it
    await page.goto("https://elsicarius.fr")
    # create a screenshot of the page and save it
    await page.screenshot({"path": "python.png"})
    # close the browser
    await browser.close()

print("Starting...")
asyncio.get_event_loop().run_until_complete(main())
print("Screenshot has been taken")