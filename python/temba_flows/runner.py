from __future__ import absolute_import, unicode_literals

import datetime
import phonenumbers
import pytz
import regex

from abc import ABCMeta, abstractmethod
from datetime import timedelta
from enum import Enum
from temba_expressions import conversions
from temba_expressions.evaluator import Evaluator, EvaluationContext, EvaluationStrategy
from .definition.flow import RuleSet
from .exceptions import FlowRunException, FlowLoopException


DEFAULT_EVALUATOR = Evaluator(expression_prefix='@',
                              allowed_top_levels=('channel', 'contact', 'date', 'extra', 'flow', 'step'))


class Org(object):
    """
    An organization - used to provide additional information about how a flow should be run
    """
    def __init__(self, country, primary_language, timezone, date_style, is_anon):
        self.country = country
        self.primary_language = primary_language
        self.timezone = timezone
        self.date_style = date_style
        self.is_anon = is_anon

    @classmethod
    def from_json(cls, json_obj):
        return cls(json_obj['country'],
                   json_obj['primary_language'],
                   json_obj['timezone'],
                   json_obj['date_style'],
                   json_obj['anon'])

    def to_json(self):
        return {'country': self.country, 'primary_language': self.primary_language, 'timezone': self.timezone,
                'date_style': self.date_style, 'anon': self.is_anon}


class Field(object):
    """
    A contact field
    """
    class ValueType(Enum):
        TEXT = 'T'
        DECIMAL = 'N'
        DATETIME = 'D'
        STATE = 'S'
        DISTRICT = 'I'

        def __init__(self, code):
            self.code = code

        @classmethod
        def from_code(cls, code):
            for name, val in cls.__members__.iteritems():
                if code == val.code:
                    return val
            return None

    def __init__(self, key, label, value_type):
        self.key = key
        self.label = label
        self.value_type = value_type
        self.is_new = True


class Contact(object):
    """
    A contact that can participate in a flow
    """
    def __init__(self, uuid, name, urns, groups, fields, language):
        self.uuid = uuid
        self.name = name
        self.urns = urns
        self.groups = groups
        self.fields = fields
        self.language = language

    @classmethod
    def from_json(cls, json_obj):
        return cls(json_obj.get('uuid', None),
                   json_obj['name'],
                   [ContactUrn.from_string(u) for u in json_obj['urns']],
                   set(json_obj['groups']),
                   json_obj['fields'],
                   json_obj.get('language', None))

    def to_json(self):
        return {'uuid': self.uuid,
                'name': self.name,
                'urns': [unicode(u) for u in self.urns],
                'groups': list(self.groups),
                'fields': self.fields,
                'language': self.language}

    def get_first_name(self, org):
        if not self.name:
            return self.get_urn_display(org)
        else:
            names = self.name.split()
            if len(names) > 1:
                return names[0]
            else:
                return self.name

    def set_first_name(self, first_name):
        if not self.name:
            self.name = first_name
        else:
            names = self.name.split()
            names = [first_name] + names[1:]
            self.name = " ".join(names)

    def get_display(self, org, full=False):
        """
        Gets a displayable name or URN for the contact. If available, org can be provided to avoid having to fetch it
        again based on the contact.
        """
        if self.name:
            return self.name
        elif org.is_anon:
            return self.get_anon_identifier()
        else:
            return self.get_urn_display(org=org, full=full)

    def get_urn(self, schemes=None):
        """
        Gets the highest priority matching URN for this contact
        """
        if schemes is not None:
            for urn in self.urns:
                if urn.scheme in schemes:
                    return urn
            return None
        else:
            # otherwise return highest priority of any scheme
            return self.urns[0] if self.urns else None

    def get_urn_display(self, org, scheme=None, full=False):
        """
        Gets a displayable URN for the contact. If available, org can be provided to avoid having to fetch it again
        based on the contact.
        """
        if org.is_anon:
            return self.get_anon_identifier()

        schemes = [scheme] if scheme else None
        urn = self.get_urn(schemes)
        return urn.get_display(org=org, full=full) if urn else ''

    def get_anon_identifier(self):
        # TODO where can we get the usual anon identifier from? Is UUID an ok substitute?
        return self.uuid

    def build_context(self, run, container):
        """
        Builds the evaluation context for this contact
        :param run: the current run state
        :param container: the containing evaluation context
        :return: the context
        """
        context = {
            '*': self.get_display(run.org, False),
            'name': self.name,
            'first_name': self.get_first_name(run.org),
            'tel_e164': self.get_urn_display(run.org, ContactUrn.Scheme.TEL, True),
            'groups': ",".join(self.groups),
            'uuid': self.uuid,
            'language': self.language
        }

        # add all URNs
        for scheme in ContactUrn.Scheme.__members__.values():
            context[unicode(scheme.name).lower()] = self.get_urn_display(run.org, scheme, False)

        # add all fields
        for key, raw_value in self.fields.iteritems():
            field = run.get_or_create_field(key)

            if field and field.value_type == Field.ValueType.DATETIME:
                as_datetime = conversions.to_datetime(raw_value, container)
                value = conversions.to_string(as_datetime, container)
            else:
                value = raw_value

            context[key] = value

        return context


class ContactUrn(object):
    """
    A URN for a contact (e.g. a telephone number or twitter handle)
    """
    class Scheme(Enum):
        TEL = 1
        TWITTER = 2

    ANON_MASK = '********'

    def __init__(self, scheme, path):
        self.scheme = scheme
        self.path = path

    @classmethod
    def from_string(cls, urn):
        """
        Parses a URN from a string
        :param urn: the string, e.g. tel:+260964153686, twitter:joe
        :return: the parsed URN
        """
        parts = urn.split(':', 2)
        scheme = ContactUrn.Scheme[parts[0].upper()]
        return ContactUrn(scheme, parts[1])

    def get_display(self, org, full=False):
        """
        Gets a representation of the URN for display
        """
        if org.is_anon:
            return self.ANON_MASK

        if self.scheme == ContactUrn.Scheme.TEL and not full:
            # if we don't want a full tell, see if we can show the national format instead
            try:
                if self.path and self.path[0] == '+':
                    return phonenumbers.format_number(phonenumbers.parse(self.path, None),
                                                      phonenumbers.PhoneNumberFormat.NATIONAL)
            except Exception:
                pass

        return self.path

    def __eq__(self, other):
        return self.scheme == other.scheme and self.path == other.path

    def __unicode__(self):
        return '%s:%s' % (unicode(self.scheme.name).lower(), self.path)


class Input(object):

    def __init__(self, value, time=None):
        self.value = value
        self.time = time if time else datetime.datetime.now(tz=pytz.UTC)

    def build_context(self, container, contact_context):
        """
        Builds the evaluation context for this input
        :param container: the evaluation context
        :param contact_context: the context
        :return:
        """
        as_text = self.get_value_as_text(container)

        return {
            '*': as_text,
            'value': as_text,
            'time': conversions.to_string(self.time, container),
            'contact': contact_context
        }

    def get_value_as_text(self, context):
        """
        Gets the input value as text which can be matched by rules
        :param context: the evaluation context
        :return: the text value
        """
        return conversions.to_string(self.value, context)


class Location(object):
    """
    Simple location model
    """
    class Level(Enum):
        STATE = 1
        DISTRICT = 2

    def __init__(self, osm_id, name, level):
        self.osm_id = osm_id
        self.name = name
        self.level = level

    class Resolver(object):
        __metaclass__ = ABCMeta

        @abstractmethod
        def resolve(self, text, country, level, parent):
            """
            Resolves a location name from the given input
            :param text: the text to parse
            :param country: the 2-digit country code
            :param level: the level
            :param parent: the parent location (may be null)
            :return: the location or null if no such location exists
            """
            pass


class Step(object):
    """
    A step taken by a contact or surveyor in a flow run
    """
    def __init__(self, node, arrived_on):
        self.node = node
        self.arrived_on = arrived_on
        self.left_on = None
        self.rule_result = None
        self.actions = []
        self.errors = []

    def add_action_result(self, action_result):
        if action_result.performed:
            self.actions.append(action_result.performed)

        if action_result.errors:
            self.errors += action_result.errors


class Value(object):
    """
    Holds the result of a contact's last visit to a ruleset
    """
    def __init__(self, value, category, text, time):
        self.value = value
        self.category = category
        self.text = text
        self.time = time

    def build_context(self, container):
        return {
            '*': self.value,
            'value': self.value,
            'category': self.category,
            'text': self.text,
            'time': conversions.to_string(self.time, container)
        }


class RunState(object):
    """
    Represents state of a flow run after visiting one or more nodes in the flow
    """
    class State(Enum):
        IN_PROGRESS = 1
        COMPLETED = 2
        WAIT_MESSAGE = 3

    def __init__(self, org, fields, contact, flow):
        self.org = org
        self.fields = fields
        self.contact = contact
        self.started = datetime.datetime.now(tz=pytz.UTC)
        self.steps = []
        self.values = {}
        self.extra = {}
        self.state = RunState.State.IN_PROGRESS
        self.flow = flow

    @classmethod
    def from_json(cls, json_obj, flow):
        """
        Restores a run state from JSON
        :param json_obj: the JSON containing a serialized run state
        :param flow: the flow the run state is for
        :return: the run state
        """
        # TODO
        pass

    def to_json(self):
        """
        Serializes this run state to JSON
        """
        # TODO
        pass

    def build_context(self, input):
        context = EvaluationContext({}, self.org.timezone, self.org.date_style)

        contact_context = self.contact.build_context(self, context)

        if input is not None:
            context.put_variable("step", input.build_context(context, contact_context))

        context.put_variable("date", self.build_date_context(context, datetime.datetime.now(tz=self.org.timezone)))
        context.put_variable("contact", contact_context)
        context.put_variable("extra", self.extra)

        flow_context = {}
        values = []
        for key, value in self.values.iteritems():
            flow_context[key] = value.build_context(context)
            values.append("%s: %s" % (key, value))
        flow_context['*'] = "\n".join(values)

        context.put_variable("flow", flow_context)

        return context

    def update_value(self, rule_set, result, time):
        """
        Updates a value in response to a rule match
        :param rule_set: the rule set
        :param result: the rule match result
        :param time: the time from the input
        :return:
        """
        key = regex.sub(r'[^a-z0-9]+', '_', rule_set.label.lower())
        self.values[key] = Value(result.value, result.category, result.text, time)

    @staticmethod
    def build_date_context(container, now):
        """
        Builds the date context (i.e. @date.now, @date.today, ...)
        """
        as_date = now.date()
        as_datetime_str = conversions.to_string(now, container)
        as_date_str = conversions.to_string(as_date, container)

        return {
            '*': as_datetime_str,
            'now': as_datetime_str,
            'today': as_date_str,
            'tomorrow': conversions.to_string(as_date + timedelta(days=1), container),
            'yesterday': conversions.to_string(as_date - timedelta(days=1), container)
        }

    def get_completed_steps(self):
        """
        Gets the completed steps, i.e. those where the contact left the node or a terminal node
        """
        completed = []
        for step in self.steps:
            if step.is_completed or self.state == RunState.State.COMPLETED:
                completed.append(step)
        return completed

    def get_or_create_field(self, key):
        # TODO get this into a map for efficiency
        for field in self.fields:
            if field.key == key:
                return field

        field = Field(key, key.title(), Field.ValueType.TEXT)
        self.fields.append(field)
        return field

    def get_created_fields(self):
        return [f for f in self.fields if f.is_new]


class Runner(object):
    """
    The flow runner
    """
    def __init__(self, template_evaluator=DEFAULT_EVALUATOR, location_resolver=None):
        self.template_evaluator = template_evaluator
        self.location_resolver = location_resolver

    def start(self, org, fields, contact, flow):
        """
        Starts a new run
        :param org: the org
        :param fields: the contact fields
        :param contact: the contact
        :param flow: the flow
        :return: the run state
        """
        run = RunState(org, fields, contact, flow)
        return self.resume(run, None)

    def resume(self, run, input):
        """
        Resumes an existing run with new input
        :param run: the previous run state
        :param input: the new input
        :return: the updated run state
        """
        if run.state == RunState.State.COMPLETED:
            raise FlowRunException("Cannot resume a completed run state")

        last_step = run.steps[-1] if len(run.steps) > 0 else None

        # reset steps list so that it doesn't grow forever in a never-ending flow
        run.steps = []

        if last_step:
            current_node = last_step.node  # we're resuming an existing run
        else:
            current_node = run.flow.entry  # we're starting a new run
            if not current_node:
                raise FlowRunException("Flow has no entry point")

        # tracks nodes visited so we can detect loops
        nodes_visited = []  # TODO ordered set?

        while current_node:
            # if we're resuming a previously paused step, then use its arrived on value
            if last_step and len(nodes_visited) == 0:
                arrived_on = last_step.arrived_on
            else:
                arrived_on = datetime.datetime.now(tz=pytz.UTC)

            # create new step for this node
            step = Step(current_node, arrived_on)
            run.steps.append(step)

            # should we pause at this node?
            if isinstance(current_node, RuleSet):
                if current_node.is_pause() and len(nodes_visited) > 0:
                    run.state = RunState.State.WAIT_MESSAGE
                    return run

            # check for an non-pausing loop
            if current_node in nodes_visited:
                raise FlowLoopException(nodes_visited)
            else:
                nodes_visited.append(current_node)

            next_node = current_node.visit(self, run, step, input)

            if next_node:
                # if we have a next node, then record leaving this one
                step.left_on = datetime.datetime.now(tz=pytz.UTC)
            else:
                # if not then we've completed this flow
                run.setState(RunState.State.COMPLETED)

            current_node = next_node

        return run

    def substitute_variables(self, text, context):
        """
        Performs variable substitution on the the given text
        :param text: the text, e.g. "Hi @contact.name"
        :param context: the evaluation context
        :return: the evaluated template, e.g. "Hi Joe"
        """
        return self.template_evaluator.evaluate_template(text, context)

    def substitute_variables_if_available(self, text, context):
        """
        Performs partial variable substitution on the the given text
        :param text: the text, e.g. "Hi @contact.name"
        :param context: the evaluation context
        :return: the evaluated template, e.g. "Hi Joe"
        """
        return self.template_evaluator.evaluate_template(text, context, False, EvaluationStrategy.RESOLVE_AVAILABLE)

    def parse_location(self, text, country, level, parent=None):
        """
        Parses a location from the given text
        :param text: the text containing a location name
        :param country: the 2-digit country code
        :param level: the level
        :param parent: the parent location (may be null)
        :return: the location or null if no such location exists
        """
        if self.location_resolver:
            return self.location_resolver.resolve(text, country, level, parent)
        return None

    def update_contact_field(self, run, key, value):
        """
        Updates a field on the contact for the given run
        :param run: the current run state
        :param key: the field key
        :param value: the field value
        """
        field = run.get_or_create_field(key)
        actual_value = None

        if field.value_type in (Field.ValueType.TEXT, Field.ValueType.DECIMAL, Field.ValueType.DATETIME):
            actual_value = value
        elif field.value_type == Field.ValueType.STATE:
            state = self.location_resolver.resolve(value, run.org.country, Location.Level.STATE, None)
            if state:
                actual_value = state.name
        elif field.value_type == Field.ValueType.DISTRICT:
            state_field = self.get_state_field(run)
            if state_field:
                state_name = run.contact.fields.get(state_field.key, None)
                if state_name:
                    state = self.location_resolver.resolve(state_name, run.org.country, Location.Level.STATE, None)
                    if state:
                        district = self.location_resolver.resolve(value, run.org.country, Location.Level.DISTRICT, state)
                        if district:
                            actual_value = district.name

        run.contact.fields[key] = actual_value

    def update_extra(self, run, values):
        """
        Updates the extra key values for the given run state
        :param run: the run state
        :param values: the key values
        """
        run.extra.update(values)

    def get_state_field(self, run):
        # TODO this mimics what we currently do in RapidPro but needs changed
        for field in run.fields:
            if field.value_type == Field.ValueType.STATE:
                return field
        return None
