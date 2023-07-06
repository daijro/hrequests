from . import page


async def new_context(inst, proxy, faker, mock_human, user_agent, **launch_arguments):
    # Spawning a new Context for more options
    context = await inst.main_browser.new_context(
        locale='en-US',
        geolocation={'longitude': proxy.longitude, 'latitude': proxy.latitude, 'accuracy': 0.7},
        timezone_id=proxy.timezone,
        permissions=['geolocation'],
        screen={'width': faker.avail_width, 'height': faker.avail_height},
        user_agent=user_agent,
        viewport={'width': faker.width, 'height': faker.height},
        proxy=proxy.browser_proxy,
        http_credentials={'username': proxy.username, 'password': proxy.password}
        if proxy.username
        else None,
        **launch_arguments,
    )

    if mock_human:
        await mock_context(inst, context, proxy, faker)
    return context


async def mock_context(inst, context, proxy, faker) -> None:
    async def page_mocker(**launch_arguments):
        return await page.new_page(inst, context, proxy, faker, **launch_arguments)

    context._new_page = context.new_page
    context.new_page = page_mocker
