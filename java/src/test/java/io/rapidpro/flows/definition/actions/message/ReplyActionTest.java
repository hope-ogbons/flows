package io.rapidpro.flows.definition.actions.message;

import io.rapidpro.flows.definition.TranslatableText;
import io.rapidpro.flows.definition.actions.Action;
import io.rapidpro.flows.definition.actions.BaseActionTest;
import io.rapidpro.flows.runner.Input;
import io.rapidpro.flows.utils.JsonUtils;
import org.junit.Test;

import static org.hamcrest.Matchers.*;
import static org.junit.Assert.assertThat;

/**
 * Test for {@link ReplyAction}
 */
public class ReplyActionTest extends BaseActionTest {

    @Test
    public void fromJson() {
        ReplyAction action = (ReplyAction) JsonUtils.getGson().fromJson("{\"type\":\"reply\",\"msg\":{\"fre\":\"Bonjour\"}}", Action.class);

        assertThat(action.getMsg(), is(new TranslatableText("fre", "Bonjour")));
    }

    @Test
    public void execute() {
        ReplyAction action = new ReplyAction(new TranslatableText("Hi @contact.first_name you said @step.value"));

        Action.Result result = action.execute(m_runner, m_run, Input.of("Yes"));
        assertThat(result.getErrors(), empty());

        ReplyAction performed = (ReplyAction) result.getPerformed();
        assertThat(performed.getMsg(), is(new TranslatableText("Hi Joe you said Yes")));

        // still send if message has errors
        action = new ReplyAction(new TranslatableText("@(badexpression)"));

        result = action.execute(m_runner, m_run, Input.of("Yes"));
        assertThat(result.getErrors(), contains("Undefined variable: badexpression"));

        performed = (ReplyAction) result.getPerformed();
        assertThat(performed.getMsg(), is(new TranslatableText("@(badexpression)")));
    }
}
