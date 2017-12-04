package io.rapidpro.flows.definition.tests.numeric;

import com.google.gson.JsonElement;
import io.rapidpro.flows.definition.tests.BaseTestTest;
import io.rapidpro.flows.definition.tests.Test;
import io.rapidpro.flows.utils.JsonUtils;

import java.math.BigDecimal;

import static org.hamcrest.Matchers.is;
import static org.junit.Assert.assertThat;

/**
 * Test for {@link GreaterThanTest}
 */
public class GreaterThanTestTest extends BaseTestTest {

    @org.junit.Test
    public void toAndFromJson() throws Exception {
        JsonElement elm = JsonUtils.object("type", "gt", "test", "32");
        GreaterThanTest test = (GreaterThanTest) Test.fromJson(elm, m_deserializationContext);
        assertThat(test.getTest(), is("32"));

        assertThat(test.toJson(), is(elm));
    }

    @org.junit.Test
    public void evaluate() {
        GreaterThanTest test = new GreaterThanTest("32 ");
        assertTest(test, "3l", false, null);
        assertTest(test, "32", false, null);
        assertTest(test, "33", true, new BigDecimal(33));

        // test can be an expression
        test = new GreaterThanTest("@(contact.age - 2)");

        assertTest(test, "3l", false, null);
        assertTest(test, "32", false, null);
        assertTest(test, "33", true, new BigDecimal(33));
    }
}
