# Prospecting Pipeline Migration Troubleshooting

## 🚨 Common Issues & Solutions

### Issue: Check constraint "prospects_status_check" violation

**Error:** `ERROR: 23514: check constraint "prospects_status_check" of relation "prospects" is violated by some row`

**Cause:** The constraint was being added before existing data was properly migrated.

**Solution:** The updated migration script now:
1. Updates all existing data first (including NULL values)
2. Then adds the constraint
3. Uses `ELSE 'new_leads'` to handle any unexpected status values

### Issue: Table "prospect_tasks" does not exist

**Error:** `relation "prospect_tasks" does not exist`

**Cause:** Migration didn't complete successfully.

**Solution:**
1. Make sure you're running the complete `prospect_pipeline_migration.sql` file
2. Check Supabase SQL editor for any syntax errors
3. Ensure you have proper permissions

### Issue: Column "region" does not exist

**Error:** `column "region" does not exist`

**Cause:** Migration didn't add the new columns.

**Solution:**
1. Verify the ALTER TABLE statements executed
2. Check for syntax errors in the migration
3. Try running just the column additions separately

### Issue: Duplicate key value violates unique constraint

**Error:** `duplicate key value violates unique constraint`

**Cause:** Trying to insert duplicate unqualified reasons.

**Solution:** The migration uses `ON CONFLICT (reason_code) DO NOTHING` to handle this.

## 🧪 Testing Your Migration

Run the test script to verify everything works:

```bash
source venv/bin/activate
python test_migration.py
```

## 🔄 Manual Data Migration (If Needed)

If the automatic migration fails, you can manually migrate your data:

```sql
-- Step 1: Handle NULL status values
UPDATE prospects SET status = 'new_leads' WHERE status IS NULL;

-- Step 2: Map old statuses to new ones
UPDATE prospects SET status = CASE
    WHEN status = 'new' THEN 'new_leads'
    WHEN status = 'contacted' THEN 'first_contact'
    WHEN status = 'qualified' THEN 'follow_up'
    WHEN status = 'converted' THEN 'customer'
    ELSE 'new_leads'
END;

-- Step 3: Add the constraint
ALTER TABLE prospects ADD CONSTRAINT prospects_status_check
CHECK (status IN ('new_leads', 'first_contact', 'meeting_planned', 'follow_up', 'customer', 'ex_customer', 'contact_later', 'unqualified'));
```

## 🔍 Checking Migration Status

### Check if columns exist:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'prospects' AND column_name IN ('region', 'prospect_type', 'contact_later_date', 'unqualified_reason');
```

### Check status values:
```sql
SELECT DISTINCT status, COUNT(*) FROM prospects GROUP BY status;
```

### Check constraints:
```sql
SELECT conname, contype, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint WHERE conrelid = 'prospects'::regclass;
```

## 🚀 Next Steps After Migration

1. **Test the application**: Start your Flask app and test adding prospects
2. **Use the pipeline**: Try moving prospects through different stages
3. **Test special features**:
   - "Contact Later" scheduling
   - "Unqualified" questionnaire
   - Pipeline overview dashboard

## 📞 Support

If you continue having issues:

1. Check the Supabase logs in your project dashboard
2. Verify your SQL syntax
3. Ensure you have the necessary permissions
4. Try running smaller parts of the migration individually

The enhanced prospecting pipeline is a major upgrade - take it step by step! 🎯
