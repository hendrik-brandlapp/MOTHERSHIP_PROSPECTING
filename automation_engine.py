"""
Automation Engine for No-Code Task Automation Builder
Handles trigger evaluation, action execution, and template processing
"""

import re
import uuid
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any


class AutomationEngine:
    """Main engine for processing automation rules"""

    def __init__(self, supabase_client):
        self.supabase = supabase_client

    # =========================================================
    # TRIGGER EVALUATION
    # =========================================================

    def evaluate_status_change(self, prospect_id: str, old_status: Optional[str],
                                new_status: str, triggered_by: str) -> List[Dict]:
        """
        Called when a prospect status changes.
        Finds matching automation rules and executes their actions.
        Returns list of execution results.
        """
        results = []

        # Find enabled automation rules with status_change trigger
        rules = self._get_matching_rules('status_change')

        for rule in rules:
            try:
                trigger_config = rule.get('trigger_config', {})

                # Check if this status change matches the rule
                from_status = trigger_config.get('from_status')
                to_status = trigger_config.get('to_status')

                # Match: from_status is null (any) or matches old_status
                from_matches = from_status is None or from_status == old_status

                # Match: to_status matches new_status
                to_matches = to_status == new_status

                if from_matches and to_matches:
                    # Get prospect data
                    prospect = self._get_prospect(prospect_id)
                    if not prospect:
                        continue

                    # Check additional conditions
                    if not self._evaluate_conditions(rule, prospect):
                        continue

                    # Create lock key to prevent duplicates
                    lock_key = f"status_change:{old_status}_to_{new_status}:{date.today().isoformat()}"

                    if self._acquire_lock(rule['id'], prospect_id, lock_key):
                        # Execute the actions
                        trigger_event = {
                            'type': 'status_change',
                            'from_status': old_status,
                            'to_status': new_status,
                            'triggered_by': triggered_by,
                            'timestamp': datetime.now().isoformat()
                        }

                        result = self._execute_actions(rule, prospect, trigger_event, triggered_by)
                        results.append(result)

            except Exception as e:
                print(f"Error evaluating rule {rule.get('id')}: {str(e)}")
                results.append({
                    'rule_id': rule.get('id'),
                    'rule_name': rule.get('name'),
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def evaluate_field_change(self, prospect_id: str, field_name: str,
                               old_value: Any, new_value: Any, triggered_by: str) -> List[Dict]:
        """
        Called when a prospect field changes.
        Finds matching automation rules and executes their actions.
        """
        results = []

        # Find enabled automation rules with field_change trigger
        rules = self._get_matching_rules('field_change')

        for rule in rules:
            try:
                trigger_config = rule.get('trigger_config', {})
                target_field = trigger_config.get('field')
                change_type = trigger_config.get('change_type', 'changed')

                # Check if this field change matches
                if target_field != field_name:
                    continue

                # Check change type
                if change_type == 'set' and old_value is not None:
                    continue  # Only trigger when field is newly set
                if change_type == 'cleared' and new_value is not None:
                    continue  # Only trigger when field is cleared
                if change_type == 'changed' and old_value == new_value:
                    continue  # Only trigger when value actually changed

                # Get prospect data
                prospect = self._get_prospect(prospect_id)
                if not prospect:
                    continue

                # Check additional conditions
                if not self._evaluate_conditions(rule, prospect):
                    continue

                # Create lock key
                lock_key = f"field_change:{field_name}:{date.today().isoformat()}"

                if self._acquire_lock(rule['id'], prospect_id, lock_key):
                    trigger_event = {
                        'type': 'field_change',
                        'field': field_name,
                        'old_value': str(old_value) if old_value else None,
                        'new_value': str(new_value) if new_value else None,
                        'triggered_by': triggered_by,
                        'timestamp': datetime.now().isoformat()
                    }

                    result = self._execute_actions(rule, prospect, trigger_event, triggered_by)
                    results.append(result)

            except Exception as e:
                print(f"Error evaluating field change rule {rule.get('id')}: {str(e)}")
                results.append({
                    'rule_id': rule.get('id'),
                    'rule_name': rule.get('name'),
                    'status': 'failed',
                    'error': str(e)
                })

        return results

    def process_time_based_queue(self) -> Dict:
        """
        Process time-based automation queue.
        Called by cron job to evaluate and execute scheduled triggers.
        """
        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0,
            'details': []
        }

        try:
            # Get pending queue items that are due
            now = datetime.now().isoformat()
            queue_items = self.supabase.table('time_based_automation_queue').select(
                '*'
            ).eq('status', 'pending').lte('scheduled_at', now).execute()

            for item in (queue_items.data or []):
                results['processed'] += 1

                try:
                    # Get the automation rule
                    rule_result = self.supabase.table('automation_rules').select(
                        '*'
                    ).eq('id', item['automation_rule_id']).eq('is_enabled', True).execute()

                    if not rule_result.data:
                        # Rule disabled or deleted, cancel this queue item
                        self.supabase.table('time_based_automation_queue').update({
                            'status': 'cancelled',
                            'processed_at': datetime.now().isoformat()
                        }).eq('id', item['id']).execute()
                        continue

                    rule = rule_result.data[0]

                    # Get prospect
                    prospect = self._get_prospect(item['prospect_id'])
                    if not prospect:
                        self.supabase.table('time_based_automation_queue').update({
                            'status': 'cancelled',
                            'processed_at': datetime.now().isoformat()
                        }).eq('id', item['id']).execute()
                        continue

                    # Check if prospect still matches conditions
                    trigger_config = rule.get('trigger_config', {})
                    status_filter = trigger_config.get('status_filter', [])

                    if status_filter and prospect.get('status') not in status_filter:
                        # Prospect no longer in required status
                        self.supabase.table('time_based_automation_queue').update({
                            'status': 'cancelled',
                            'processed_at': datetime.now().isoformat()
                        }).eq('id', item['id']).execute()
                        continue

                    # Check additional conditions
                    if not self._evaluate_conditions(rule, prospect):
                        self.supabase.table('time_based_automation_queue').update({
                            'status': 'cancelled',
                            'processed_at': datetime.now().isoformat()
                        }).eq('id', item['id']).execute()
                        continue

                    # Execute actions
                    trigger_event = {
                        'type': 'time_based',
                        'event': item['reference_event'],
                        'reference_date': item['reference_date'],
                        'triggered_by': 'system',
                        'timestamp': datetime.now().isoformat()
                    }

                    execution_result = self._execute_actions(rule, prospect, trigger_event, 'system')

                    # Update queue item
                    self.supabase.table('time_based_automation_queue').update({
                        'status': 'processed',
                        'processed_at': datetime.now().isoformat()
                    }).eq('id', item['id']).execute()

                    results['succeeded'] += 1
                    results['details'].append(execution_result)

                except Exception as e:
                    results['failed'] += 1
                    self.supabase.table('time_based_automation_queue').update({
                        'status': 'failed',
                        'processed_at': datetime.now().isoformat()
                    }).eq('id', item['id']).execute()
                    print(f"Error processing queue item {item['id']}: {str(e)}")

        except Exception as e:
            print(f"Error processing time-based queue: {str(e)}")
            results['error'] = str(e)

        return results

    def schedule_time_based_triggers(self, prospect_id: str, prospect_data: Dict):
        """
        Schedule time-based triggers for a prospect.
        Called when a prospect is created or updated.
        """
        try:
            # Find enabled time-based automation rules
            rules = self._get_matching_rules('time_based')

            for rule in rules:
                trigger_config = rule.get('trigger_config', {})
                event = trigger_config.get('event', 'created_at')
                days_offset = trigger_config.get('days_offset', 7)
                status_filter = trigger_config.get('status_filter', [])

                # Check if prospect status matches filter
                if status_filter and prospect_data.get('status') not in status_filter:
                    continue

                # Calculate scheduled date based on event
                reference_date = None
                if event == 'created_at':
                    ref_str = prospect_data.get('created_at')
                    if ref_str:
                        reference_date = datetime.fromisoformat(ref_str.replace('Z', '+00:00')).date()
                elif event == 'last_contact_date':
                    ref_str = prospect_data.get('last_contact_date')
                    if ref_str:
                        reference_date = datetime.fromisoformat(ref_str).date() if 'T' in ref_str else date.fromisoformat(ref_str)
                elif event == 'status_changed_at':
                    ref_str = prospect_data.get('updated_at')
                    if ref_str:
                        reference_date = datetime.fromisoformat(ref_str.replace('Z', '+00:00')).date()

                if not reference_date:
                    reference_date = date.today()

                scheduled_at = datetime.combine(
                    reference_date + timedelta(days=days_offset),
                    datetime.min.time()
                )

                # Only schedule if in the future
                if scheduled_at > datetime.now():
                    # Check if already scheduled
                    existing = self.supabase.table('time_based_automation_queue').select(
                        'id'
                    ).eq('automation_rule_id', rule['id']).eq(
                        'prospect_id', prospect_id
                    ).eq('status', 'pending').execute()

                    if not existing.data:
                        # Schedule the trigger
                        self.supabase.table('time_based_automation_queue').insert({
                            'automation_rule_id': rule['id'],
                            'prospect_id': prospect_id,
                            'scheduled_at': scheduled_at.isoformat(),
                            'reference_event': event,
                            'reference_date': reference_date.isoformat(),
                            'status': 'pending'
                        }).execute()

        except Exception as e:
            print(f"Error scheduling time-based triggers for {prospect_id}: {str(e)}")

    # =========================================================
    # ACTION EXECUTION
    # =========================================================

    def _execute_actions(self, rule: Dict, prospect: Dict,
                         trigger_event: Dict, triggered_by: str) -> Dict:
        """Execute all actions defined in an automation rule"""
        actions = rule.get('actions', [])
        actions_executed = []
        overall_status = 'success'

        for action in actions:
            action_type = action.get('type')
            config = action.get('config', {})

            try:
                if action_type == 'create_task':
                    result = self._action_create_task(config, prospect, trigger_event, triggered_by)
                    actions_executed.append(result)
                elif action_type == 'update_prospect_status':
                    result = self._action_update_status(config, prospect)
                    actions_executed.append(result)
                else:
                    actions_executed.append({
                        'type': action_type,
                        'success': False,
                        'error': f'Unknown action type: {action_type}'
                    })
                    overall_status = 'partial'

            except Exception as e:
                actions_executed.append({
                    'type': action_type,
                    'success': False,
                    'error': str(e)
                })
                overall_status = 'partial'

        # Log the execution
        execution_id = self._log_execution(rule['id'], prospect.get('id'), trigger_event,
                                            overall_status, actions_executed)

        # Update rule execution stats
        self.supabase.table('automation_rules').update({
            'last_executed_at': datetime.now().isoformat(),
            'execution_count': rule.get('execution_count', 0) + 1,
            'updated_at': datetime.now().isoformat()
        }).eq('id', rule['id']).execute()

        return {
            'rule_id': rule['id'],
            'rule_name': rule.get('name'),
            'execution_id': execution_id,
            'status': overall_status,
            'actions_executed': actions_executed
        }

    def _action_create_task(self, config: Dict, prospect: Dict,
                            trigger_event: Dict, triggered_by: str) -> Dict:
        """Create a task from action configuration"""
        context = self._build_template_context(prospect, trigger_event, triggered_by)

        title = self._render_template(config.get('title_template', 'Task'), context)
        description = self._render_template(config.get('description_template', ''), context)
        assigned_to = self._render_template(config.get('assigned_to', ''), context)

        due_date_offset = config.get('due_date_offset_days', 1)
        due_date = (date.today() + timedelta(days=due_date_offset)).isoformat()

        task_data = {
            'title': title,
            'description': description,
            'task_type': config.get('task_type', 'follow_up'),
            'priority': config.get('priority', 3),
            'status': 'pending',
            'due_date': due_date,
            'prospect_id': prospect.get('id'),
            'assigned_to': assigned_to or triggered_by,
            'created_by': 'automation',
            'is_automated': True,
            'automation_trigger': f"automation_rule:{config.get('rule_id', 'unknown')}"
        }

        result = self.supabase.table('sales_tasks').insert(task_data).execute()

        if result.data:
            return {
                'type': 'create_task',
                'success': True,
                'task_id': result.data[0]['id'],
                'task_title': title
            }
        else:
            return {
                'type': 'create_task',
                'success': False,
                'error': 'Failed to create task'
            }

    def _action_update_status(self, config: Dict, prospect: Dict) -> Dict:
        """Update prospect status"""
        new_status = config.get('new_status')

        if not new_status:
            return {
                'type': 'update_prospect_status',
                'success': False,
                'error': 'No new_status specified'
            }

        result = self.supabase.table('prospects').update({
            'status': new_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', prospect['id']).execute()

        if result.data:
            return {
                'type': 'update_prospect_status',
                'success': True,
                'old_status': prospect.get('status'),
                'new_status': new_status
            }
        else:
            return {
                'type': 'update_prospect_status',
                'success': False,
                'error': 'Failed to update status'
            }

    # =========================================================
    # TEMPLATE PROCESSING
    # =========================================================

    def _render_template(self, template: str, context: Dict) -> str:
        """Replace {{variables}} with actual values"""
        if not template:
            return ''

        result = template
        for key, value in context.items():
            placeholder = '{{' + key + '}}'
            result = result.replace(placeholder, str(value) if value else '')

        return result

    def _build_template_context(self, prospect: Dict, trigger_event: Dict,
                                 triggered_by: str) -> Dict:
        """Build context dictionary for template rendering"""
        return {
            'prospect_name': prospect.get('name', ''),
            'prospect_status': prospect.get('status', ''),
            'prospect_address': prospect.get('address', ''),
            'prospect_region': prospect.get('region', ''),
            'salesperson': prospect.get('assigned_salesperson', ''),
            'current_user': triggered_by,
            'trigger_date': date.today().isoformat(),
            'trigger_type': trigger_event.get('type', ''),
            'from_status': trigger_event.get('from_status', ''),
            'to_status': trigger_event.get('to_status', ''),
            'field_name': trigger_event.get('field', ''),
            'new_value': trigger_event.get('new_value', '')
        }

    # =========================================================
    # HELPER METHODS
    # =========================================================

    def _get_matching_rules(self, trigger_type: str) -> List[Dict]:
        """Get enabled automation rules for a trigger type"""
        try:
            result = self.supabase.table('automation_rules').select(
                '*'
            ).eq('trigger_type', trigger_type).eq('is_enabled', True).eq('is_draft', False).execute()

            return result.data or []
        except Exception as e:
            print(f"Error fetching automation rules: {str(e)}")
            return []

    def _get_prospect(self, prospect_id: str) -> Optional[Dict]:
        """Get prospect data by ID"""
        try:
            result = self.supabase.table('prospects').select('*').eq('id', prospect_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error fetching prospect {prospect_id}: {str(e)}")
            return None

    def _evaluate_conditions(self, rule: Dict, prospect: Dict) -> bool:
        """Evaluate additional conditions on a rule"""
        conditions = rule.get('conditions', [])

        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator', 'equals')
            value = condition.get('value')

            prospect_value = prospect.get(field)

            if operator == 'equals':
                if str(prospect_value) != str(value):
                    return False
            elif operator == 'not_equals':
                if str(prospect_value) == str(value):
                    return False
            elif operator == 'contains':
                if value not in str(prospect_value or ''):
                    return False
            elif operator == 'not_contains':
                if value in str(prospect_value or ''):
                    return False
            elif operator == '>=':
                try:
                    if float(prospect_value or 0) < float(value):
                        return False
                except (ValueError, TypeError):
                    return False
            elif operator == '<=':
                try:
                    if float(prospect_value or 0) > float(value):
                        return False
                except (ValueError, TypeError):
                    return False
            elif operator == 'is_set':
                if not prospect_value:
                    return False
            elif operator == 'is_not_set':
                if prospect_value:
                    return False

        return True

    def _acquire_lock(self, rule_id: str, prospect_id: str, lock_key: str) -> bool:
        """Acquire execution lock to prevent duplicates"""
        try:
            self.supabase.table('automation_execution_lock').insert({
                'automation_rule_id': rule_id,
                'prospect_id': prospect_id,
                'lock_key': lock_key
            }).execute()
            return True
        except Exception as e:
            if 'duplicate' in str(e).lower() or 'unique' in str(e).lower():
                return False  # Already executed
            print(f"Error acquiring lock: {str(e)}")
            return False

    def _log_execution(self, rule_id: str, prospect_id: str, trigger_event: Dict,
                       status: str, actions_executed: List[Dict]) -> Optional[str]:
        """Log execution to automation_executions table"""
        try:
            result = self.supabase.table('automation_executions').insert({
                'automation_rule_id': rule_id,
                'prospect_id': prospect_id,
                'trigger_event': trigger_event,
                'status': status,
                'actions_executed': actions_executed,
                'executed_at': datetime.now().isoformat()
            }).execute()

            return result.data[0]['id'] if result.data else None
        except Exception as e:
            print(f"Error logging execution: {str(e)}")
            return None

    # =========================================================
    # TEST/DRY RUN
    # =========================================================

    def test_automation(self, rule_id: str, sample_prospect_id: Optional[str] = None) -> Dict:
        """
        Test an automation without actually executing actions.
        Returns what WOULD happen.
        """
        try:
            # Get the rule
            rule_result = self.supabase.table('automation_rules').select('*').eq('id', rule_id).execute()
            if not rule_result.data:
                return {'error': 'Automation rule not found'}

            rule = rule_result.data[0]

            # Get sample prospect
            if sample_prospect_id:
                prospect = self._get_prospect(sample_prospect_id)
                if not prospect:
                    return {'error': 'Sample prospect not found'}
            else:
                # Find a prospect that would match
                prospect = self._find_sample_prospect(rule)
                if not prospect:
                    return {'error': 'No matching prospect found for testing'}

            # Simulate trigger event
            trigger_type = rule.get('trigger_type')
            trigger_config = rule.get('trigger_config', {})

            if trigger_type == 'status_change':
                trigger_event = {
                    'type': 'status_change',
                    'from_status': trigger_config.get('from_status'),
                    'to_status': trigger_config.get('to_status'),
                    'triggered_by': 'test_user'
                }
            elif trigger_type == 'time_based':
                trigger_event = {
                    'type': 'time_based',
                    'event': trigger_config.get('event'),
                    'days_offset': trigger_config.get('days_offset'),
                    'triggered_by': 'system'
                }
            elif trigger_type == 'field_change':
                trigger_event = {
                    'type': 'field_change',
                    'field': trigger_config.get('field'),
                    'change_type': trigger_config.get('change_type'),
                    'triggered_by': 'test_user'
                }
            else:
                trigger_event = {'type': trigger_type}

            # Check conditions
            conditions_pass = self._evaluate_conditions(rule, prospect)

            # Preview actions
            context = self._build_template_context(prospect, trigger_event, 'test_user')
            previewed_actions = []

            for action in rule.get('actions', []):
                action_type = action.get('type')
                config = action.get('config', {})

                if action_type == 'create_task':
                    title = self._render_template(config.get('title_template', ''), context)
                    description = self._render_template(config.get('description_template', ''), context)
                    due_days = config.get('due_date_offset_days', 1)
                    due_date = (date.today() + timedelta(days=due_days)).isoformat()

                    previewed_actions.append({
                        'type': 'create_task',
                        'preview': {
                            'title': title,
                            'description': description,
                            'task_type': config.get('task_type'),
                            'priority': config.get('priority'),
                            'due_date': due_date
                        }
                    })
                elif action_type == 'update_prospect_status':
                    previewed_actions.append({
                        'type': 'update_prospect_status',
                        'preview': {
                            'current_status': prospect.get('status'),
                            'new_status': config.get('new_status')
                        }
                    })

            return {
                'success': True,
                'would_trigger': conditions_pass,
                'prospect_used': {
                    'id': prospect.get('id'),
                    'name': prospect.get('name'),
                    'status': prospect.get('status')
                },
                'trigger_event': trigger_event,
                'conditions_evaluated': conditions_pass,
                'actions_preview': previewed_actions
            }

        except Exception as e:
            return {'error': str(e)}

    def _find_sample_prospect(self, rule: Dict) -> Optional[Dict]:
        """Find a prospect that matches the rule for testing"""
        try:
            trigger_config = rule.get('trigger_config', {})

            # Build query based on trigger type
            query = self.supabase.table('prospects').select('*')

            if rule.get('trigger_type') == 'status_change':
                # For status change, find prospect with the "from" status
                from_status = trigger_config.get('from_status')
                if from_status:
                    query = query.eq('status', from_status)

            elif rule.get('trigger_type') == 'time_based':
                status_filter = trigger_config.get('status_filter', [])
                if status_filter:
                    query = query.in_('status', status_filter)

            result = query.limit(1).execute()
            return result.data[0] if result.data else None

        except Exception as e:
            print(f"Error finding sample prospect: {str(e)}")
            return None


# Pre-built automation templates
AUTOMATION_TEMPLATES = [
    {
        "id": "first_contact_followup",
        "name": "First Contact Follow-up",
        "description": "Create email, check reply, and call tasks after first contact",
        "trigger_type": "status_change",
        "trigger_config": {"from_status": None, "to_status": "first_contact"},
        "conditions": [],
        "actions": [
            {
                "type": "create_task",
                "config": {
                    "title_template": "Send follow-up email to {{prospect_name}}",
                    "description_template": "Send personalized follow-up email with product information and next steps.",
                    "task_type": "email",
                    "priority": 2,
                    "due_date_offset_days": 1,
                    "assigned_to": "{{current_user}}"
                }
            },
            {
                "type": "create_task",
                "config": {
                    "title_template": "Check for reply from {{prospect_name}}",
                    "description_template": "Check if prospect has replied to follow-up email.",
                    "task_type": "follow_up",
                    "priority": 3,
                    "due_date_offset_days": 3,
                    "assigned_to": "{{current_user}}"
                }
            },
            {
                "type": "create_task",
                "config": {
                    "title_template": "Call {{prospect_name}}",
                    "description_template": "Phone call to discuss their needs and schedule next meeting.",
                    "task_type": "call",
                    "priority": 2,
                    "due_date_offset_days": 5,
                    "assigned_to": "{{current_user}}"
                }
            }
        ]
    },
    {
        "id": "new_customer_onboarding",
        "name": "New Customer Onboarding",
        "description": "Schedule 1-month, 3-month, and 6-month check-ins for new customers",
        "trigger_type": "status_change",
        "trigger_config": {"from_status": None, "to_status": "customer"},
        "conditions": [],
        "actions": [
            {
                "type": "create_task",
                "config": {
                    "title_template": "1-Month Check-in: {{prospect_name}}",
                    "description_template": "Contact customer: How is everything going? What could be better? Gather feedback.",
                    "task_type": "call",
                    "priority": 3,
                    "due_date_offset_days": 30,
                    "assigned_to": "{{salesperson}}"
                }
            },
            {
                "type": "create_task",
                "config": {
                    "title_template": "3-Month Follow-up: {{prospect_name}}",
                    "description_template": "Quarterly check-in to ensure satisfaction and identify new opportunities.",
                    "task_type": "call",
                    "priority": 3,
                    "due_date_offset_days": 90,
                    "assigned_to": "{{salesperson}}"
                }
            },
            {
                "type": "create_task",
                "config": {
                    "title_template": "6-Month Review: {{prospect_name}}",
                    "description_template": "Semi-annual customer review and relationship maintenance.",
                    "task_type": "meeting",
                    "priority": 3,
                    "due_date_offset_days": 180,
                    "assigned_to": "{{salesperson}}"
                }
            }
        ]
    },
    {
        "id": "no_contact_reminder",
        "name": "No Contact Reminder",
        "description": "Create reminder task if no contact for 7 days",
        "trigger_type": "time_based",
        "trigger_config": {
            "event": "last_contact_date",
            "days_offset": 7,
            "status_filter": ["first_contact", "follow_up", "meeting_planned"]
        },
        "conditions": [],
        "actions": [
            {
                "type": "create_task",
                "config": {
                    "title_template": "Re-engage {{prospect_name}} - No contact in 7 days",
                    "description_template": "This prospect hasn't been contacted in a week. Reach out to maintain the relationship.",
                    "task_type": "call",
                    "priority": 2,
                    "due_date_offset_days": 0,
                    "assigned_to": "{{salesperson}}"
                }
            }
        ]
    },
    {
        "id": "salesperson_assignment",
        "name": "Salesperson Assignment",
        "description": "Create intro task when salesperson is assigned to a prospect",
        "trigger_type": "field_change",
        "trigger_config": {
            "field": "assigned_salesperson",
            "change_type": "set"
        },
        "conditions": [],
        "actions": [
            {
                "type": "create_task",
                "config": {
                    "title_template": "Review and contact {{prospect_name}}",
                    "description_template": "You've been assigned to this prospect. Review their information and make initial contact.",
                    "task_type": "research",
                    "priority": 2,
                    "due_date_offset_days": 1,
                    "assigned_to": "{{new_value}}"
                }
            }
        ]
    }
]
