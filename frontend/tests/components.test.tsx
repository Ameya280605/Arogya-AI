import { describe, it } from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  Label,
  Input,
  Textarea,
  Select,
  Checkbox,
  FormField,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Skeleton,
  Toast,
} from "../components/ui";
import { LoginForm } from "../components/auth/LoginForm";

describe("Button Primitive", () => {
  it("renders with default props and semantic button element", () => {
    const html = renderToStaticMarkup(<Button>Action</Button>);
    assert.ok(html.includes("<button"));
    assert.ok(html.includes('type="button"'));
    assert.ok(html.includes("Action"));
    assert.ok(html.includes("primary"));
    assert.ok(html.includes("md"));
  });

  it("supports all variants", () => {
    const variants = ["primary", "secondary", "outline", "ghost", "danger"] as const;
    for (const v of variants) {
      const html = renderToStaticMarkup(<Button variant={v}>{v}</Button>);
      assert.ok(html.includes(v), `Expected variant ${v} to be rendered in class`);
    }
  });

  it("supports all sizes", () => {
    const sizes = ["sm", "md", "lg"] as const;
    for (const s of sizes) {
      const html = renderToStaticMarkup(<Button size={s}>{s}</Button>);
      assert.ok(html.includes(s), `Expected size ${s} to be rendered in class`);
    }
  });

  it("supports native button types (submit, reset)", () => {
    const htmlSubmit = renderToStaticMarkup(<Button type="submit">Submit</Button>);
    assert.ok(htmlSubmit.includes('type="submit"'));

    const htmlReset = renderToStaticMarkup(<Button type="reset">Reset</Button>);
    assert.ok(htmlReset.includes('type="reset"'));
  });

  it("handles disabled state with aria-disabled", () => {
    const html = renderToStaticMarkup(<Button disabled>Disabled Action</Button>);
    assert.ok(html.includes("disabled"));
    assert.ok(html.includes('aria-disabled="true"'));
  });

  it("renders leading and trailing icons", () => {
    const html = renderToStaticMarkup(
      <Button
        leadingIcon={<span id="lead-icon">*</span>}
        trailingIcon={<span id="trail-icon">&gt;</span>}
      >
        With Icons
      </Button>
    );
    assert.ok(html.includes('id="lead-icon"'));
    assert.ok(html.includes('id="trail-icon"'));
  });
});

describe("Badge Primitive", () => {
  it("renders text label and neutral variant by default", () => {
    const html = renderToStaticMarkup(<Badge>Verified</Badge>);
    assert.ok(html.includes("<span"));
    assert.ok(html.includes("Verified"));
    assert.ok(html.includes("neutral"));
  });

  it("renders all semantic variants", () => {
    const variants = ["neutral", "info", "success", "warning", "danger"] as const;
    for (const v of variants) {
      const html = renderToStaticMarkup(<Badge variant={v}>{v}</Badge>);
      assert.ok(html.includes(v), `Expected variant ${v} to be rendered`);
    }
  });

  it("renders with dot indicator when withDot is true", () => {
    const html = renderToStaticMarkup(<Badge withDot>Status</Badge>);
    assert.ok(html.includes('aria-hidden="true"'));
  });
});

describe("Card Composition", () => {
  it("renders full composition hierarchy", () => {
    const html = renderToStaticMarkup(
      <Card as="article">
        <CardHeader>
          <CardTitle as="h2">Card Header Title</CardTitle>
          <CardDescription>Card Description Text</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Main Card Body</p>
        </CardContent>
        <CardFooter>
          <span>Footer Status</span>
        </CardFooter>
      </Card>
    );

    assert.ok(html.includes("<article"));
    assert.ok(html.includes("<h2"));
    assert.ok(html.includes("Card Header Title"));
    assert.ok(html.includes("Card Description Text"));
    assert.ok(html.includes("Main Card Body"));
    assert.ok(html.includes("Footer Status"));
  });
});

describe("Table Semantic Structure", () => {
  it("renders valid table, headers, rows, cells, and caption", () => {
    const html = renderToStaticMarkup(
      <Table>
        <TableCaption>Synthetic observation specifications</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead>Field</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Heart Rate</TableCell>
            <TableCell>Normal</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    assert.ok(html.includes("<table"));
    assert.ok(html.includes("<caption"));
    assert.ok(html.includes("Synthetic observation specifications"));
    assert.ok(html.includes("<thead"));
    assert.ok(html.includes("<th"));
    assert.ok(html.includes('scope="col"'));
    assert.ok(html.includes("<tbody"));
    assert.ok(html.includes("<td"));
    assert.ok(html.includes("Heart Rate"));
    assert.ok(html.includes('role="region"'));
    assert.ok(html.includes('aria-label="Data Table"'));
  });
});

describe("Form Primitives", () => {
  it("renders Label with required indicator", () => {
    const html = renderToStaticMarkup(
      <Label htmlFor="test-input" required>
        Patient Identifier
      </Label>
    );
    assert.ok(html.includes('for="test-input"'));
    assert.ok(html.includes("Patient Identifier"));
    assert.ok(html.includes("*"));
  });

  it("renders Input with invalid state and attributes", () => {
    const html = renderToStaticMarkup(
      <Input id="test-input" invalid placeholder="Enter MRN" disabled />
    );
    assert.ok(html.includes('id="test-input"'));
    assert.ok(html.includes('aria-invalid="true"'));
    assert.ok(html.includes('placeholder="Enter MRN"'));
    assert.ok(html.includes("disabled"));
  });

  it("renders Textarea with invalid state", () => {
    const html = renderToStaticMarkup(
      <Textarea id="notes" invalid rows={4} defaultValue="Clinical summary" />
    );
    assert.ok(html.includes("<textarea"));
    assert.ok(html.includes('id="notes"'));
    assert.ok(html.includes('aria-invalid="true"'));
    assert.ok(html.includes("Clinical summary"));
  });

  it("renders Select dropdown with options", () => {
    const html = renderToStaticMarkup(
      <Select id="triage-level" defaultValue="routine">
        <option value="routine">Routine</option>
        <option value="urgent">Urgent</option>
      </Select>
    );
    assert.ok(html.includes("<select"));
    assert.ok(html.includes('id="triage-level"'));
    assert.ok(html.includes('value="routine"'));
    assert.ok(html.includes("Urgent"));
  });

  it("renders Checkbox with custom visual indicator and description", () => {
    const html = renderToStaticMarkup(
      <Checkbox
        id="consent"
        label="Patient Consent Verified"
        description="Explicit consent documented for research review"
        defaultChecked
      />
    );
    assert.ok(html.includes('type="checkbox"'));
    assert.ok(html.includes('id="consent"'));
    assert.ok(html.includes("Patient Consent Verified"));
    assert.ok(html.includes("Explicit consent documented"));
    assert.ok(html.includes("checked"));
  });

  it("renders FormField wrapping Input with error message", () => {
    const html = renderToStaticMarkup(
      <FormField
        label="Medical Record Number"
        htmlFor="mrn"
        required
        error="MRN must follow the standard format"
      >
        <Input id="mrn" invalid />
      </FormField>
    );
    assert.ok(html.includes("Medical Record Number"));
    assert.ok(html.includes('id="mrn-error"'));
    assert.ok(html.includes('role="alert"'));
    assert.ok(html.includes("MRN must follow the standard format"));
  });

  it("renders FormField wrapping Input with helper text when no error", () => {
    const html = renderToStaticMarkup(
      <FormField
        label="Search Query"
        htmlFor="query"
        helperText="Enter medical concept or ICD code"
      >
        <Input id="query" />
      </FormField>
    );
    assert.ok(html.includes('id="query-helper"'));
    assert.ok(html.includes("Enter medical concept or ICD code"));
  });
});

describe("Dialog Primitive", () => {
  it("renders dialog trigger when closed", () => {
    const html = renderToStaticMarkup(
      <Dialog open={false}>
        <DialogTrigger>Open Dialog</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog Title</DialogTitle>
          <DialogDescription>Dialog Description</DialogDescription>
        </DialogContent>
      </Dialog>
    );

    assert.ok(html.includes("Open Dialog"));
    assert.ok(!html.includes("Dialog Title"));
  });

  it("renders dialog content with aria-modal and roles when open", () => {
    const html = renderToStaticMarkup(
      <Dialog open={true}>
        <DialogTrigger>Open Dialog</DialogTrigger>
        <DialogContent>
          <DialogTitle>Confirmation Required</DialogTitle>
          <DialogDescription>Please review the research parameters.</DialogDescription>
          <DialogClose>Dismiss</DialogClose>
        </DialogContent>
      </Dialog>
    );

    assert.ok(html.includes('role="dialog"'));
    assert.ok(html.includes('aria-modal="true"'));
    assert.ok(html.includes("Confirmation Required"));
    assert.ok(html.includes("Please review the research parameters."));
    assert.ok(html.includes("Dismiss"));
  });
});

describe("Tabs Primitive", () => {
  it("renders active tab content and accessibility roles", () => {
    const html = renderToStaticMarkup(
      <Tabs defaultValue="specs">
        <TabsList>
          <TabsTrigger value="specs">Specifications</TabsTrigger>
          <TabsTrigger value="roadmap">Roadmap</TabsTrigger>
        </TabsList>
        <TabsContent value="specs">
          <p>Specifications Content</p>
        </TabsContent>
        <TabsContent value="roadmap">
          <p>Roadmap Content</p>
        </TabsContent>
      </Tabs>
    );

    assert.ok(html.includes('role="tablist"'));
    assert.ok(html.includes('role="tab"'));
    assert.ok(html.includes('aria-selected="true"'));
    assert.ok(html.includes('role="tabpanel"'));
    assert.ok(html.includes("Specifications Content"));
    assert.ok(!html.includes("Roadmap Content"));
  });
});

describe("Skeleton & Toast Primitives", () => {
  it("renders Skeleton with aria-hidden and variants", () => {
    const htmlRect = renderToStaticMarkup(<Skeleton width="100%" height={24} />);
    assert.ok(htmlRect.includes('aria-hidden="true"'));
    assert.ok(htmlRect.includes("height:24px"));

    const htmlCirc = renderToStaticMarkup(<Skeleton variant="circular" width={40} height={40} />);
    assert.ok(htmlCirc.includes("circular"));
  });

  it("renders Toast with accessible status role and dismiss button", () => {
    const html = renderToStaticMarkup(
      <Toast
        title="Protocol Updated"
        description="Changes preserved to research registry."
        variant="info"
        onClose={() => {}}
      />
    );

    assert.ok(html.includes('role="status"'));
    assert.ok(html.includes('aria-live="polite"'));
    assert.ok(html.includes("Protocol Updated"));
    assert.ok(html.includes("Changes preserved to research registry."));
    assert.ok(html.includes('aria-label="Dismiss notification"'));
  });

  it("renders alert Toast for danger variant", () => {
    const html = renderToStaticMarkup(
      <Toast
        title="Validation Error"
        description="Missing required physiological parameters."
        variant="danger"
      />
    );

    assert.ok(html.includes('role="alert"'));
    assert.ok(html.includes('aria-live="assertive"'));
    assert.ok(html.includes("Validation Error"));
  });
});

describe("LoginForm Component", () => {
  it("renders username, password, submit button, and quick login presets", () => {
    const html = renderToStaticMarkup(
      <LoginForm
        title="Clinical Authentication"
        description="Sign in to verify credentials"
      />
    );

    assert.ok(html.includes("Clinical Authentication"));
    assert.ok(html.includes("Sign in to verify credentials"));
    assert.ok(html.includes('id="login-username"'));
    assert.ok(html.includes('id="login-password"'));
    assert.ok(html.includes('type="password"'));
    assert.ok(html.includes("Doctor Reviewer"));
    assert.ok(html.includes("System Administrator"));
    assert.ok(html.includes("Research Scientist"));
  });
});

