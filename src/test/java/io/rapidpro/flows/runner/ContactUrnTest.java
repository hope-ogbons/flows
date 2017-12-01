package io.rapidpro.flows.runner;

import com.google.gson.JsonElement;
import com.google.gson.JsonPrimitive;
import io.rapidpro.flows.BaseFlowsTest;
import org.junit.Test;

import static org.hamcrest.Matchers.is;
import static org.junit.Assert.assertThat;

/**
 * Test for {@link ContactUrn}
 */
public class ContactUrnTest extends BaseFlowsTest {

    @Test
    public void toAndFromString() {
        ContactUrn urn = ContactUrn.fromString("tel:+260964153686");

        assertThat(urn.getScheme(), is(ContactUrn.Scheme.TEL));
        assertThat(urn.getPath(), is("+260964153686"));
        assertThat(urn.toString(), is("tel:+260964153686"));

        urn = ContactUrn.fromString("telegram:1234");
        assertThat(urn.getScheme(), is(ContactUrn.Scheme.TELEGRAM));
        assertThat(urn.getPath(), is("1234"));
        assertThat(urn.toString(), is("telegram:1234"));

        urn = ContactUrn.fromString("mailto:name@domain.com");
        assertThat(urn.getScheme(), is(ContactUrn.Scheme.MAILTO));
        assertThat(urn.getPath(), is("name@domain.com"));
        assertThat(urn.toString(), is("mailto:name@domain.com"));

        urn = ContactUrn.fromString("ext:EXT123");
        assertThat(urn.getScheme(), is(ContactUrn.Scheme.EXT));
        assertThat(urn.getPath(), is("EXT123"));

    }

    @Test
    public void toAndFromJson() {
        ContactUrn urn = ContactUrn.fromJson(new JsonPrimitive("tel:+260964153686"));

        assertThat(urn.getScheme(), is(ContactUrn.Scheme.TEL));
        assertThat(urn.getPath(), is("+260964153686"));

        assertThat(urn.toJson(), is((JsonElement) new JsonPrimitive("tel:+260964153686")));
    }

    @Test
    public void normalized() {
        ContactUrn raw = new ContactUrn(ContactUrn.Scheme.TEL, " 078-383-5665 ");
        assertThat(raw.normalized(m_org), is(new ContactUrn(ContactUrn.Scheme.TEL, "+250783835665")));

        raw = new ContactUrn(ContactUrn.Scheme.TWITTER, "  @bOb ");
        assertThat(raw.normalized(m_org), is(new ContactUrn(ContactUrn.Scheme.TWITTER, "bob")));

        raw = new ContactUrn(ContactUrn.Scheme.MAILTO, " nAme@DomAIN.com ");
        assertThat(raw.normalized(m_org), is(new ContactUrn(ContactUrn.Scheme.MAILTO, "name@domain.com")));

        raw = new ContactUrn(ContactUrn.Scheme.EXT, " ExTErnal123 ");
        assertThat(raw.normalized(m_org), is(new ContactUrn(ContactUrn.Scheme.EXT, "ExTErnal123")));

    }
}
