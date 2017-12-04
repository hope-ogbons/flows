package io.rapidpro.flows.definition.tests.date;

import com.google.gson.JsonElement;
import io.rapidpro.flows.definition.tests.BaseTestTest;
import io.rapidpro.flows.definition.tests.Test;
import io.rapidpro.flows.utils.JsonUtils;
import org.threeten.bp.LocalDate;

import static org.hamcrest.Matchers.is;
import static org.junit.Assert.assertThat;

/**
 * Test for {@link HasDateTest}
 */
public class HasDateTestTest extends BaseTestTest {

    @org.junit.Test
    public void toAndFromJson() throws Exception {
        JsonElement elm = JsonUtils.object("type", "date");
        HasDateTest test = (HasDateTest) Test.fromJson(elm, m_deserializationContext);

        assertThat(test.toJson(), is(elm));
    }

    @org.junit.Test
    public void evaluate() {
        HasDateTest test = new HasDateTest();

        assertTest(test, "December 14, 1992", true, LocalDate.of(1992, 12, 14));
        assertTest(test, "sometime on 24/8/15", true, LocalDate.of(2015, 8, 24));

        assertTest(test, "no date in this text", false, null);
        assertTest(test, "123", false, null);  // this differs from old implementation which was a bit too flexible regarding dates
    }
}
