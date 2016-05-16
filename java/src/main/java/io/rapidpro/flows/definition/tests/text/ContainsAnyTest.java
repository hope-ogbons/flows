package io.rapidpro.flows.definition.tests.text;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import io.rapidpro.expressions.EvaluationContext;
import io.rapidpro.expressions.utils.ExpressionUtils;
import io.rapidpro.flows.definition.Flow;
import io.rapidpro.flows.definition.FlowParseException;
import io.rapidpro.flows.definition.TranslatableText;
import io.rapidpro.flows.definition.tests.Test;
import io.rapidpro.flows.runner.RunState;
import io.rapidpro.flows.runner.Runner;
import io.rapidpro.flows.utils.JsonUtils;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.SortedSet;
import java.util.TreeSet;

/**
 * Test that returns whether the text contains any of the given words
 */
public class ContainsAnyTest extends ContainsTest {

    public static final String TYPE = "contains_any";

    public ContainsAnyTest(TranslatableText test) {
        super(test);
    }

    /**
     * @see Test#fromJson(JsonElement, Flow.DeserializationContext)
     */
    public static ContainsAnyTest fromJson(JsonElement elm, Flow.DeserializationContext context) throws FlowParseException {
        JsonObject obj = elm.getAsJsonObject();
        return new ContainsAnyTest(TranslatableText.fromJson(obj.get("test")));
    }

    @Override
    public JsonElement toJson() {
        return JsonUtils.object("type", TYPE, "test", m_test.toJson());
    }

    /**
     * @see TranslatableTest#evaluateForLocalized(Runner, RunState, EvaluationContext, String, String)
     */
    @Override
    protected Test.Result evaluateForLocalized(Runner runner, RunState run, EvaluationContext context, String text, String localizedTest) {
        localizedTest = runner.substituteVariables(localizedTest, context).getOutput();

        // tokenize our test
        String[] tests = ExpressionUtils.tokenize(localizedTest.toLowerCase());

        // tokenize our input
        String[] words = ExpressionUtils.tokenize(text.toLowerCase());
        String[] rawWords = ExpressionUtils.tokenize(text);

        // run through each of our tests
        SortedSet<Integer> matches = new TreeSet<>();
        for (String test : tests) {
            findMatches(matches, test, words, rawWords);
        }

        // we are a match if at least one test matches
        if (matches.size() > 0) {
            // build our actual matches as strings
            ArrayList<String> matchingWords = new ArrayList<>();
            for (int matchIndex: matches){
                matchingWords.add(rawWords[matchIndex]);
            }
            return Test.Result.match(StringUtils.join(matchingWords, " "));
        } else {
            return Test.Result.NO_MATCH;
        }
    }
}
