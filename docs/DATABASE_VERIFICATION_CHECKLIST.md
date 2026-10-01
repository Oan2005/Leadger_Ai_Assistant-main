# Database Verification Checklist

The repository does not contain the deployed Supabase/PostgreSQL schema,
migrations, or RLS policy definitions. The following checks must be completed
against the actual environment before production approval.

## RLS

- [ ] `companies` policies enforce tenant ownership.
- [ ] `users` policies enforce tenant ownership.
- [ ] `documents` policies enforce tenant ownership.
- [ ] `conversations` policies enforce tenant ownership.
- [ ] `conversation_analysis` policies are limited through the parent conversation.
- [ ] `invitations` policies prevent cross-company reads and writes.
- [ ] Service-role backend operations are intentionally allowed and protected.

## Foreign keys

- [ ] `users.company_id` references `companies.company_id`.
- [ ] `documents.company_id` references `companies.company_id`.
- [ ] `conversations.company_id` references `companies.company_id`.
- [ ] `conversations.user_id` references `users.user_id`.
- [ ] `conversation_analysis.conversation_id` references `conversations.conversation_id`.
- [ ] `conversation_documents.document_id` references `documents.document_id`.
- [ ] `invitations.company_id` references `companies.company_id`.

## Delete behavior

- [ ] User deletion behavior is compatible with retained conversations and audit history.
- [ ] Document soft deletion preserves intended conversation/document history.
- [ ] Company deletion has an intentional policy for users, documents, invitations, and conversations.
- [ ] Conversation deletion has an intentional policy for conversation analysis and document links.
- [ ] No cascade can delete records belonging to another company.

## Consistency verification

- [ ] A failed Pinecone operation leaves the PostgreSQL status unchanged.
- [ ] A failed PostgreSQL status update is visible as an explicit API failure.
- [ ] Upload cleanup removes vectors when document-record creation fails.
- [ ] Production and staging credentials are confirmed before destructive integration tests.
