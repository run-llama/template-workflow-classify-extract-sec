-- name: GetMessages :many
SELECT (message_role, content) FROM chat_sessions
WHERE session_id = ?;

-- name: CreateMessage :one
INSERT INTO chat_sessions (
  session_id, message_role, content
) VALUES (
  ?, ?, ?
)
RETURNING *;