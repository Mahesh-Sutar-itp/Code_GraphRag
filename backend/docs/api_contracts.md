# API Contracts:

## Ingestion Pipeline
1. POST /index-repository

---

## Inference Pipeline

1. POST /resolve-query
```json
Request Payload

{
    "user_id"=<id of the user>,
    "session_id"=<id of the session>,
    "query"=<prompt from user>
}
```

```json
Response Payload

{
    "status": <success/error>,
    "code": <status code (currently only 500/200)>,
    "msg": <error_msg/query_answer>
}
```