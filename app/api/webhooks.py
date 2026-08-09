import httpx

FB_GRAPH_URL = "https://graph.facebook.com/v21.0/me/messages"


async def send_messenger_reply(page_access_token: str, recipient_id: str, text: str) -> None:
    """Send a reply back to Messenger via the Facebook Send API."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            FB_GRAPH_URL,
            params={"access_token": page_access_token},
            json={"recipient": {"id": recipient_id}, "message": {"text": text}},
        )
        # Don't let a Facebook-side failure crash the webhook response to Meta —
        # log it so it's visible in Render logs, same way the OpenAI call is logged.
        if resp.status_code != 200:
            print(f"Messenger send failed [{resp.status_code}]: {resp.text}")


@public_router.post("")
async def receive(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: AgentVectorStore = Depends(get_vector_store),
    llm_provider: LLMProvider = Depends(get_llm_provider),
):
    config = db.query(AgentWebhookConfig).filter_by(agent_id=agent_id).one_or_none()
    if not config:
        raise HTTPException(404, "Webhook is not configured")

    body = await request.json()
    entries = body.get("entry", [])

    # Keep sender + message paired together — sender lives on the event, not the message.
    events = [
        event
        for entry in entries
        for event in entry.get("messaging", [])
        if event.get("message", {}).get("text")
    ]

    replies = []
    agent = agent_service.get_agent(db, agent_id)

    for event in events:
        sender_id = event.get("sender", {}).get("id")
        text = event["message"]["text"]

        conversation = conversation_service.record_user_message(
            db, agent=agent, conversation_id=None, content=text,
            sender_type="api", sender_origin="messenger",
        )
        result = chat_service.generate_response(
            db, agent=agent, message=text,
            embedding_provider=embedding_provider,
            vector_store=vector_store, llm_provider=llm_provider,
        )
        conversation_service.record_agent_message(
            db, conversation=conversation, content=result.answer, sources=result.sources,
        )

        # Actually deliver the reply back to Messenger.
        if sender_id and config.page_access_token:
            await send_messenger_reply(config.page_access_token, sender_id, result.answer)

        replies.append({"recipient_id": sender_id, "message": result.answer})

    return {"received": len(replies), "replies": replies}