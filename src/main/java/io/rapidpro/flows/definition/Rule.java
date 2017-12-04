package io.rapidpro.flows.definition;

import com.google.gson.JsonObject;
import io.rapidpro.expressions.EvaluationContext;
import io.rapidpro.flows.definition.tests.Test;
import io.rapidpro.flows.runner.RunState;
import io.rapidpro.flows.runner.Runner;
import io.rapidpro.flows.utils.JsonUtils;
import org.apache.commons.lang3.StringUtils;

/**
 * A matchable rule in a rule set
 */
public class Rule extends Flow.Element implements Flow.ConnectionStart {

    protected Test m_test;

    protected TranslatableText m_category;

    protected Flow.Node m_destination;

    /**
     * Creates a rule from the given JSON object
     * @param obj the JSON object
     * @param context the deserialization context
     * @return the rule
     */
    public static Rule fromJson(JsonObject obj, Flow.DeserializationContext context) throws FlowParseException {
        Rule rule = new Rule();
        rule.m_uuid = obj.get("uuid").getAsString();
        rule.m_test = Test.fromJson(obj.get("test").getAsJsonObject(), context);
        rule.m_category = TranslatableText.fromJson(obj.get("category"));

        String destinationUuid = JsonUtils.getAsString(obj, "destination");
        if (StringUtils.isNotEmpty(destinationUuid)) {
            context.needsDestination(rule, destinationUuid);
        }
        return rule;
    }

    /**
     * Checks whether this rule is a match for the given input
     * @param runner the flow runner
     * @param run the current run state
     * @param context the evaluation context
     * @param input the input
     * @return the test result
     */
    public Test.Result matches(Runner runner, RunState run, EvaluationContext context, String input) {
        return m_test.evaluate(runner, run, context, input);
    }

    public Test getTest() {
        return m_test;
    }

    public TranslatableText getCategory() {
        return m_category;
    }

    @Override
    public Flow.Node getDestination() {
        return m_destination;
    }

    @Override
    public void setDestination(Flow.Node destination) {
        this.m_destination = destination;
    }

}
