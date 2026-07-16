\set ON_ERROR_STOP on
BEGIN TRANSACTION READ ONLY;

COPY (
    SELECT row_value
    FROM (
        SELECT
            'asset|' || id::text || '|' || tag || '|' || category::text || '|' ||
            model || '|' || status::text || '|' || region::text || '|' ||
            to_char(last_synced_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US')
            AS row_value
        FROM public.assets
        UNION ALL
        SELECT
            'user|' || id::text || '|' || name || '|' || email || '|' ||
            department::text
        FROM public.users
        UNION ALL
        SELECT
            'checkout|' || id::text || '|' || asset_id::text || '|' ||
            user_id::text || '|' ||
            to_char(checked_out_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') ||
            '|' || coalesce(
                to_char(checked_in_at AT TIME ZONE 'UTC',
                        'YYYY-MM-DD"T"HH24:MI:SS.US'),
                ''
            )
        FROM public.checkouts
    ) rows
    ORDER BY row_value
) TO STDOUT;

ROLLBACK;
