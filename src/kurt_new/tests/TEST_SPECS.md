# Kurt_new Framework Test Specifications

## Overview

This document describes all unit and integration tests needed for the kurt_new framework.

---

## 1. test_llm_step.py - LLMStep Core

### 1.1 Initialization

```python
class TestLLMStepInit:
    """Test LLMStep initialization behaviors."""

    def test_queue_created_with_correct_name():
        """Queue name is {step_name}_queue."""
        step = LLMStep(name="extract", ...)
        assert step.queue.name == "extract_queue"

    def test_queue_concurrency_setting():
        """Queue concurrency matches parameter."""
        step = LLMStep(name="extract", concurrency=5, ...)
        assert step.queue.concurrency == 5

    def test_queue_priority_disabled_by_default():
        """Priority is disabled unless explicitly enabled."""
        step = LLMStep(name="extract", ...)
        assert step._priority_enabled is False

    def test_queue_priority_enabled():
        """Priority can be enabled via parameter."""
        step = LLMStep(name="extract", priority_enabled=True, ...)
        assert step._priority_enabled is True

    def test_step_function_registered():
        """_process_row is a callable after init."""
        step = LLMStep(name="extract", ...)
        assert callable(step._process_row)

    def test_hooks_default_to_noop():
        """Without hooks param, uses NoopStepHooks."""
        step = LLMStep(name="extract", ...)
        assert isinstance(step._hooks, NoopStepHooks)

    def test_custom_hooks_assigned():
        """Custom hooks are used when provided."""
        custom_hooks = MockStepHooks()
        step = LLMStep(name="extract", hooks=custom_hooks, ...)
        assert step._hooks is custom_hooks
```

### 1.2 Prompt Building

```python
class TestPromptBuilding:
    """Test _build_prompt() method."""

    def test_template_formatting_single_column():
        """Single column is formatted into template."""
        step = LLMStep(
            input_columns=["content"],
            prompt_template="Extract from: {content}",
            ...
        )
        result = step._build_prompt({"content": "hello world"})
        assert result == "Extract from: hello world"

    def test_template_formatting_multiple_columns():
        """Multiple columns are formatted into template."""
        step = LLMStep(
            input_columns=["title", "body"],
            prompt_template="Title: {title}\nBody: {body}",
            ...
        )
        result = step._build_prompt({"title": "Test", "body": "Content"})
        assert result == "Title: Test\nBody: Content"

    def test_missing_column_defaults_to_empty():
        """Missing columns default to empty string."""
        step = LLMStep(
            input_columns=["content", "missing"],
            prompt_template="{content} - {missing}",
            ...
        )
        result = step._build_prompt({"content": "hello"})
        assert result == "hello - "

    def test_extra_columns_ignored():
        """Extra columns in row_dict are ignored."""
        step = LLMStep(
            input_columns=["content"],
            prompt_template="{content}",
            ...
        )
        result = step._build_prompt({"content": "hello", "extra": "ignored"})
        assert result == "hello"
```

### 1.3 LLM Calling

```python
class TestLLMCalling:
    """Test _call_llm() method."""

    def test_llm_fn_invoked_with_prompt():
        """llm_fn is called with the prompt string."""
        mock_fn = Mock(return_value=MockSchema(field="value"))
        step = LLMStep(name="test", llm_fn=mock_fn, ...)
        step._call_llm("test prompt")
        mock_fn.assert_called_once_with("test prompt")

    def test_pydantic_result_converted_to_dict():
        """Pydantic model result is converted via model_dump()."""
        step = LLMStep(
            llm_fn=lambda p: MockSchema(field="value"),
            ...
        )
        result = step._call_llm("prompt")
        assert result == {"field": "value"}
        assert isinstance(result, dict)

    def test_dict_result_passed_through():
        """Dict results are passed through directly."""
        step = LLMStep(
            llm_fn=lambda p: {"field": "value"},
            ...
        )
        result = step._call_llm("prompt")
        assert result == {"field": "value"}

    def test_metrics_tuple_extracts_result():
        """(result, metrics) tuple: result is extracted."""
        step = LLMStep(
            llm_fn=lambda p: (MockSchema(field="value"), {"tokens_in": 100}),
            ...
        )
        result = step._call_llm("prompt")
        assert result == {"field": "value"}

    def test_metrics_tuple_tracks_tokens_in():
        """(result, metrics) tuple: tokens_in is tracked."""
        step = LLMStep(
            llm_fn=lambda p: (MockSchema(), {"tokens_in": 150}),
            ...
        )
        step._call_llm("prompt")
        assert step._last_tokens_in == 150

    def test_metrics_tuple_tracks_tokens_out():
        """(result, metrics) tuple: tokens_out is tracked."""
        step = LLMStep(
            llm_fn=lambda p: (MockSchema(), {"tokens_out": 75}),
            ...
        )
        step._call_llm("prompt")
        assert step._last_tokens_out == 75

    def test_metrics_tuple_tracks_cost():
        """(result, metrics) tuple: cost is tracked."""
        step = LLMStep(
            llm_fn=lambda p: (MockSchema(), {"cost": 0.05}),
            ...
        )
        step._call_llm("prompt")
        assert step._last_cost == 0.05

    def test_metrics_alternative_keys():
        """Metrics support alternative key names (input_tokens, output_tokens)."""
        step = LLMStep(
            llm_fn=lambda p: (MockSchema(), {"input_tokens": 100, "output_tokens": 50}),
            ...
        )
        step._call_llm("prompt")
        assert step._last_tokens_in == 100
        assert step._last_tokens_out == 50

    def test_missing_llm_fn_raises():
        """RuntimeError raised when llm_fn is None."""
        step = LLMStep(name="test", llm_fn=None, ...)
        with pytest.raises(RuntimeError, match="llm_fn is required"):
            step._call_llm("prompt")

    def test_invalid_return_type_raises():
        """TypeError raised for invalid return types."""
        step = LLMStep(
            llm_fn=lambda p: "invalid string",
            ...
        )
        with pytest.raises(TypeError):
            step._call_llm("prompt")
```

### 1.4 Row Preparation

```python
class TestRowPreparation:
    """Test prepare_fn behavior."""

    def test_prepare_fn_called_before_prompt():
        """prepare_fn is called before building prompt."""
        call_order = []

        def prepare(row):
            call_order.append("prepare")
            row["content"] = row["content"].upper()
            return row

        step = LLMStep(
            prepare_fn=prepare,
            input_columns=["content"],
            prompt_template="{content}",
            llm_fn=lambda p: (call_order.append("llm"), MockSchema())[1],
            ...
        )
        # Execute via _process_row (need DBOS mock)
        assert call_order == ["prepare", "llm"]

    def test_prepare_fn_receives_copy():
        """prepare_fn receives a copy, not the original row."""
        original = {"content": "original"}

        def prepare(row):
            row["content"] = "modified"
            return row

        step = LLMStep(prepare_fn=prepare, ...)
        # After processing, original should be unchanged
        assert original["content"] == "original"

    def test_prepare_fn_can_add_columns():
        """prepare_fn can add new columns to the row."""
        def prepare(row):
            row["extra"] = "added"
            return row

        step = LLMStep(
            prepare_fn=prepare,
            input_columns=["content", "extra"],
            prompt_template="{content} {extra}",
            ...
        )
        result = step._build_prompt(prepare({"content": "hello"}))
        assert "added" in result

    def test_no_prepare_fn_uses_row_directly():
        """Without prepare_fn, row is used as-is."""
        step = LLMStep(prepare_fn=None, ...)
        # Row should pass through unchanged
```

### 1.5 run() Method

```python
class TestLLMStepRun:
    """Test LLMStep.run() method (requires DBOS mock)."""

    def test_all_rows_enqueued():
        """All DataFrame rows are enqueued to the queue."""
        df = pd.DataFrame({"content": ["a", "b", "c"]})
        step = LLMStep(...)
        with mock_dbos():
            step.run(df)
        assert step.queue.enqueue_count == 3

    def test_results_collected_in_order():
        """Results map back to correct row indices."""
        df = pd.DataFrame({"content": ["a", "b", "c"]})
        step = LLMStep(...)
        with mock_dbos():
            result_df = step.run(df)
        assert len(result_df) == 3
        # Check idx mapping

    def test_output_columns_added():
        """Output schema fields are added as columns."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(output_schema=MockSchema, ...)  # MockSchema has "field"
        with mock_dbos():
            result_df = step.run(df)
        assert "field" in result_df.columns

    def test_status_column_added():
        """{step_name}_status column is added."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(name="extract", ...)
        with mock_dbos():
            result_df = step.run(df)
        assert "extract_status" in result_df.columns

    def test_successful_rows_have_success_status():
        """Successful rows have status='success'."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(name="extract", llm_fn=lambda p: MockSchema(), ...)
        with mock_dbos():
            result_df = step.run(df)
        assert result_df["extract_status"].iloc[0] == "success"

    def test_error_rows_have_error_status():
        """Failed rows have status='error'."""
        def failing_fn(prompt):
            raise ValueError("LLM error")

        step = LLMStep(name="extract", llm_fn=failing_fn, ...)
        with mock_dbos():
            result_df = step.run(pd.DataFrame({"content": ["a"]}))
        assert result_df["extract_status"].iloc[0] == "error"

    def test_partial_success_mixed_status():
        """DataFrame can have mix of success/error rows."""
        call_count = [0]
        def sometimes_fail(prompt):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("fail")
            return MockSchema()

        step = LLMStep(llm_fn=sometimes_fail, ...)
        with mock_dbos():
            result_df = step.run(pd.DataFrame({"content": ["a", "b", "c"]}))
        statuses = result_df["step_status"].tolist()
        assert "success" in statuses
        assert "error" in statuses

    def test_priority_uses_set_enqueue_options():
        """With priority, uses SetEnqueueOptions context."""
        step = LLMStep(priority_enabled=True, ...)
        with mock_dbos() as dbos_mock:
            step.run(df, priority=1)
        dbos_mock.SetEnqueueOptions.assert_called_with(priority=1)

    def test_no_priority_normal_enqueue():
        """Without priority, normal enqueue."""
        step = LLMStep(priority_enabled=False, ...)
        with mock_dbos() as dbos_mock:
            step.run(df, priority=1)  # priority ignored
        dbos_mock.SetEnqueueOptions.assert_not_called()

    def test_original_dataframe_unchanged():
        """Original DataFrame is not mutated."""
        df = pd.DataFrame({"content": ["a", "b"]})
        original_columns = list(df.columns)
        step = LLMStep(...)
        with mock_dbos():
            step.run(df)
        assert list(df.columns) == original_columns
```

### 1.6 @llm_step Decorator

```python
class TestLLMStepDecorator:
    """Test @llm_step decorator."""

    def test_returns_llm_step_instance():
        """Decorator returns an LLMStep instance."""
        @llm_step(
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
        )
        def my_step(row):
            return row

        assert isinstance(my_step, LLMStep)

    def test_name_from_function():
        """Step name is derived from function name."""
        @llm_step(...)
        def extract_entities(row):
            return row

        assert extract_entities.name == "extract_entities"

    def test_prepare_fn_captured():
        """Decorated function is used as prepare_fn."""
        @llm_step(...)
        def my_step(row):
            row["modified"] = True
            return row

        assert my_step._prepare_fn is not None

    def test_all_params_forwarded():
        """All decorator params are forwarded to LLMStep."""
        @llm_step(
            input_columns=["a", "b"],
            prompt_template="{a} {b}",
            output_schema=MockSchema,
            concurrency=10,
            priority_enabled=True,
        )
        def my_step(row):
            return row

        assert my_step.input_columns == ["a", "b"]
        assert my_step.concurrency == 10
        assert my_step._priority_enabled is True
```

---

## 2. test_hooks.py - Lifecycle Hooks

### 2.1 StepHooks Base

```python
class TestStepHooksBase:
    """Test StepHooks base class."""

    def test_on_start_returns_none():
        """on_start returns None by default."""
        hooks = StepHooks()
        result = hooks.on_start(step_name="test", total=10, concurrency=3)
        assert result is None

    def test_on_row_success_returns_none():
        """on_row_success returns None by default."""
        hooks = StepHooks()
        result = hooks.on_row_success(
            step_name="test", idx=0, total=10,
            latency_ms=100, prompt="p", tokens_in=10,
            tokens_out=5, cost=0.01, result={}
        )
        assert result is None

    def test_on_row_error_returns_none():
        """on_row_error returns None by default."""
        hooks = StepHooks()
        result = hooks.on_row_error(
            step_name="test", idx=0, total=10,
            latency_ms=100, prompt="p", tokens_in=10,
            tokens_out=5, cost=0.01, error=ValueError("err")
        )
        assert result is None

    def test_on_result_returns_none():
        """on_result returns None by default."""
        hooks = StepHooks()
        result = hooks.on_result(
            step_name="test", idx=0, total=10,
            status="success", error=None
        )
        assert result is None

    def test_on_end_returns_none():
        """on_end returns None by default."""
        hooks = StepHooks()
        result = hooks.on_end(
            step_name="test", successful=8, total=10, errors=["e1", "e2"]
        )
        assert result is None
```

### 2.2 NoopStepHooks

```python
class TestNoopStepHooks:
    """Test NoopStepHooks does nothing."""

    def test_all_methods_callable():
        """All hook methods are callable without error."""
        hooks = NoopStepHooks()
        hooks.on_start(step_name="t", total=1, concurrency=1)
        hooks.on_row_success(step_name="t", idx=0, total=1, latency_ms=0,
                            prompt="", tokens_in=0, tokens_out=0, cost=0, result={})
        hooks.on_row_error(step_name="t", idx=0, total=1, latency_ms=0,
                          prompt="", tokens_in=0, tokens_out=0, cost=0, error=Exception())
        hooks.on_result(step_name="t", idx=0, total=1, status="success", error=None)
        hooks.on_end(step_name="t", successful=1, total=1, errors=[])
```

### 2.3 CompositeStepHooks

```python
class TestCompositeStepHooks:
    """Test CompositeStepHooks fans out to all hooks."""

    def test_on_start_calls_all_hooks():
        """on_start is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_start(step_name="test", total=10, concurrency=3)
        hook1.on_start.assert_called_once()
        hook2.on_start.assert_called_once()

    def test_on_row_success_calls_all_hooks():
        """on_row_success is called on all hooks with same args."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_row_success(
            step_name="test", idx=0, total=10,
            latency_ms=100, prompt="p", tokens_in=10,
            tokens_out=5, cost=0.01, result={"key": "val"}
        )
        hook1.on_row_success.assert_called_once()
        hook2.on_row_success.assert_called_once()

    def test_on_row_error_calls_all_hooks():
        """on_row_error is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        err = ValueError("test")
        composite.on_row_error(
            step_name="test", idx=0, total=10,
            latency_ms=100, prompt="p", tokens_in=10,
            tokens_out=5, cost=0.01, error=err
        )
        hook1.on_row_error.assert_called_once()
        hook2.on_row_error.assert_called_once()

    def test_on_result_calls_all_hooks():
        """on_result is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_result(step_name="test", idx=0, total=10, status="success", error=None)
        hook1.on_result.assert_called_once()
        hook2.on_result.assert_called_once()

    def test_on_end_calls_all_hooks():
        """on_end is called on all hooks."""
        hook1, hook2 = Mock(), Mock()
        composite = CompositeStepHooks([hook1, hook2])
        composite.on_end(step_name="test", successful=8, total=10, errors=["e1"])
        hook1.on_end.assert_called_once()
        hook2.on_end.assert_called_once()

    def test_none_hooks_filtered():
        """None values in hooks list are filtered out."""
        hook1 = Mock()
        composite = CompositeStepHooks([hook1, None, None])
        composite.on_start(step_name="test", total=1, concurrency=1)
        hook1.on_start.assert_called_once()

    def test_empty_hooks_list():
        """Empty hooks list doesn't error."""
        composite = CompositeStepHooks([])
        composite.on_start(step_name="test", total=1, concurrency=1)
        # No error raised
```

---

## 3. test_mocking.py - Mock Utilities

### 3.1 mock_llm Context Manager

```python
class TestMockLLM:
    """Test mock_llm context manager."""

    def test_replaces_llm_fn_in_context():
        """llm_fn is replaced within context."""
        step = LLMStep(llm_fn=original_fn, ...)
        mock_fn = Mock(return_value=MockSchema())

        with mock_llm([step], mock_fn):
            assert step._llm_fn is mock_fn

    def test_restores_llm_fn_after_context():
        """Original llm_fn is restored after context exits."""
        original = Mock()
        step = LLMStep(llm_fn=original, ...)

        with mock_llm([step], Mock()):
            pass

        assert step._llm_fn is original

    def test_restores_on_exception():
        """Original llm_fn is restored even if exception raised."""
        original = Mock()
        step = LLMStep(llm_fn=original, ...)

        try:
            with mock_llm([step], Mock()):
                raise ValueError("test")
        except ValueError:
            pass

        assert step._llm_fn is original

    def test_multiple_steps():
        """Works with multiple steps."""
        step1 = LLMStep(name="step1", ...)
        step2 = LLMStep(name="step2", ...)
        mock_fn = Mock()

        with mock_llm([step1, step2], mock_fn):
            assert step1._llm_fn is mock_fn
            assert step2._llm_fn is mock_fn

    def test_default_factory_returns_empty():
        """Without factory, returns empty dict."""
        step = LLMStep(...)
        with mock_llm([step]):
            result = step._llm_fn("prompt")
        assert result == {}
```

### 3.2 create_response_factory

```python
class TestCreateResponseFactory:
    """Test create_response_factory function."""

    def test_str_field_default():
        """String fields default to 'mock_{field_name}'."""
        class Schema(BaseModel):
            name: str

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.name == "mock_name"

    def test_float_field_default():
        """Float fields default to 0.85."""
        class Schema(BaseModel):
            score: float

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.score == 0.85

    def test_int_field_default():
        """Int fields default to 42."""
        class Schema(BaseModel):
            count: int

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.count == 42

    def test_list_field_default():
        """List fields default to empty list."""
        class Schema(BaseModel):
            items: list[str]

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.items == []

    def test_other_field_default_none():
        """Other types default to None."""
        class Schema(BaseModel):
            data: dict | None

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.data is None

    def test_custom_field_values():
        """Custom field_values override defaults."""
        class Schema(BaseModel):
            name: str
            score: float

        factory = create_response_factory(Schema, {"name": "custom", "score": 0.99})
        result = factory("prompt")
        assert result.name == "custom"
        assert result.score == 0.99

    def test_partial_custom_values():
        """Can override some fields, others use defaults."""
        class Schema(BaseModel):
            name: str
            count: int

        factory = create_response_factory(Schema, {"name": "custom"})
        result = factory("prompt")
        assert result.name == "custom"
        assert result.count == 42  # default
```

### 3.3 create_content_aware_factory

```python
class TestCreateContentAwareFactory:
    """Test create_content_aware_factory function."""

    def test_keyword_match_returns_values():
        """Matching keyword returns specified values."""
        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result = factory("This is a positive review")
        assert result.sentiment == "happy"

    def test_keyword_case_insensitive():
        """Keyword matching is case-insensitive."""
        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"POSITIVE": {"sentiment": "happy"}},
        )
        result = factory("this is positive")
        assert result.sentiment == "happy"

    def test_no_match_uses_default():
        """No keyword match falls back to default factory."""
        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result = factory("neutral text")
        assert result.sentiment == "mock_sentiment"

    def test_first_match_wins():
        """First matching keyword is used."""
        class Schema(BaseModel):
            value: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={
                "first": {"value": "one"},
                "second": {"value": "two"},
            },
        )
        result = factory("first and second")
        assert result.value == "one"

    def test_default_values_param():
        """default_values are used for unspecified fields."""
        class Schema(BaseModel):
            sentiment: str
            confidence: float

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
            default_values={"confidence": 0.95},
        )
        result = factory("positive text")
        assert result.sentiment == "happy"
        assert result.confidence == 0.95
```

### 3.4 Factories with Metrics

```python
class TestFactoriesWithMetrics:
    """Test *_with_metrics factory variants."""

    def test_response_factory_returns_tuple():
        """create_response_factory_with_metrics returns (result, metrics)."""
        class Schema(BaseModel):
            name: str

        factory = create_response_factory_with_metrics(Schema)
        result = factory("prompt")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_response_factory_result_is_model():
        """First element is the Pydantic model."""
        class Schema(BaseModel):
            name: str

        factory = create_response_factory_with_metrics(Schema)
        result, metrics = factory("prompt")
        assert isinstance(result, Schema)

    def test_response_factory_metrics_dict():
        """Second element is metrics dict."""
        factory = create_response_factory_with_metrics(MockSchema)
        result, metrics = factory("prompt")
        assert "tokens_in" in metrics
        assert "tokens_out" in metrics
        assert "cost" in metrics

    def test_metrics_scaled_by_prompt_length():
        """tokens_in is scaled by prompt length."""
        factory = create_response_factory_with_metrics(
            MockSchema,
            metrics={"tokens_in": 100, "tokens_out": 50, "cost": 0.01}
        )
        _, metrics_short = factory("short")
        _, metrics_long = factory("a" * 400)
        assert metrics_long["tokens_in"] > metrics_short["tokens_in"]

    def test_content_aware_with_metrics():
        """create_content_aware_factory_with_metrics returns tuple."""
        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory_with_metrics(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result, metrics = factory("positive text")
        assert result.sentiment == "happy"
        assert "tokens_in" in metrics

    def test_custom_metrics_values():
        """Custom metrics values are used."""
        factory = create_response_factory_with_metrics(
            MockSchema,
            metrics={"tokens_in": 200, "tokens_out": 100, "cost": 0.05}
        )
        _, metrics = factory("x")
        assert metrics["tokens_out"] == 100
        assert metrics["cost"] == 0.05
```

---

## 4. test_tracing.py - LLMTracer

### 4.1 LLMTracer.record()

```python
class TestLLMTracerRecord:
    """Test LLMTracer.record() method."""

    def test_inserts_trace_record(db_session):
        """Record is inserted into llm_traces table."""
        tracer = LLMTracer()
        tracer.record(
            prompt="test prompt",
            response="test response",
            model="gpt-4",
            latency_ms=100,
        )

        traces = tracer.query()
        assert len(traces) == 1
        assert traces[0]["prompt"] == "test prompt"

    def test_all_fields_stored(db_session):
        """All provided fields are stored."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p",
            response="r",
            model="gpt-4",
            latency_ms=150,
            tokens_in=100,
            tokens_out=50,
            cost=0.02,
            workflow_id="wf-123",
            step_name="extract",
            provider="openai",
            structured_output='{"key": "val"}',
            error="error msg",
            retry_count=2,
        )

        trace = tracer.query()[0]
        assert trace["model"] == "gpt-4"
        assert trace["latency_ms"] == 150
        assert trace["input_tokens"] == 100
        assert trace["output_tokens"] == 50
        assert trace["cost"] == 0.02
        assert trace["workflow_id"] == "wf-123"
        assert trace["step_name"] == "extract"
        assert trace["provider"] == "openai"
        assert trace["error"] == "error msg"
        assert trace["retry_count"] == 2

    def test_workflow_id_defaults_to_unknown(db_session):
        """workflow_id defaults to 'unknown' when not in DBOS context."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        trace = tracer.query()[0]
        assert trace["workflow_id"] == "unknown"

    def test_step_name_defaults_to_unknown(db_session):
        """step_name defaults to 'unknown'."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        trace = tracer.query()[0]
        assert trace["step_name"] == "unknown"

    def test_total_tokens_computed(db_session):
        """total_tokens = tokens_in + tokens_out."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p", response="r", model="m", latency_ms=0,
            tokens_in=100, tokens_out=50
        )
        trace = tracer.query()[0]
        assert trace["total_tokens"] == 150
```

### 4.2 LLMTracer.query()

```python
class TestLLMTracerQuery:
    """Test LLMTracer.query() method."""

    def test_returns_all_traces(db_session):
        """Returns all traces when no filters."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0)

        traces = tracer.query()
        assert len(traces) == 2

    def test_filter_by_workflow_id(db_session):
        """Filter by workflow_id."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0, workflow_id="wf1")
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0, workflow_id="wf2")

        traces = tracer.query(workflow_id="wf1")
        assert len(traces) == 1
        assert traces[0]["prompt"] == "p1"

    def test_filter_by_step_name(db_session):
        """Filter by step_name."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0, step_name="step1")
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0, step_name="step2")

        traces = tracer.query(step_name="step1")
        assert len(traces) == 1

    def test_limit_parameter(db_session):
        """Respects limit parameter."""
        tracer = LLMTracer()
        for i in range(10):
            tracer.record(prompt=f"p{i}", response="r", model="m", latency_ms=0)

        traces = tracer.query(limit=5)
        assert len(traces) == 5

    def test_ordered_by_created_at_desc(db_session):
        """Results ordered by created_at descending."""
        tracer = LLMTracer()
        tracer.record(prompt="first", response="r", model="m", latency_ms=0)
        tracer.record(prompt="second", response="r", model="m", latency_ms=0)

        traces = tracer.query()
        assert traces[0]["prompt"] == "second"  # most recent first
```

### 4.3 LLMTracer.stats()

```python
class TestLLMTracerStats:
    """Test LLMTracer.stats() method."""

    def test_total_calls(db_session):
        """Counts total calls."""
        tracer = LLMTracer()
        for _ in range(5):
            tracer.record(prompt="p", response="r", model="m", latency_ms=0)

        stats = tracer.stats()
        assert stats["total_calls"] == 5

    def test_token_totals(db_session):
        """Sums token counts."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, tokens_in=100, tokens_out=50)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, tokens_in=200, tokens_out=100)

        stats = tracer.stats()
        assert stats["total_tokens_in"] == 300
        assert stats["total_tokens_out"] == 150

    def test_total_cost(db_session):
        """Sums cost."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, cost=0.01)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, cost=0.02)

        stats = tracer.stats()
        assert stats["total_cost"] == 0.03

    def test_latency_stats(db_session):
        """Computes avg, min, max latency."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=100)
        tracer.record(prompt="p", response="r", model="m", latency_ms=200)
        tracer.record(prompt="p", response="r", model="m", latency_ms=300)

        stats = tracer.stats()
        assert stats["avg_latency_ms"] == 200
        assert stats["min_latency_ms"] == 100
        assert stats["max_latency_ms"] == 300

    def test_success_error_counts(db_session):
        """Counts success vs error."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, error="failed")

        stats = tracer.stats()
        assert stats["success_count"] == 2
        assert stats["error_count"] == 1

    def test_filter_by_workflow_id(db_session):
        """Stats can be filtered by workflow_id."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, workflow_id="wf1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, workflow_id="wf2")

        stats = tracer.stats(workflow_id="wf1")
        assert stats["total_calls"] == 1
```

### 4.4 LLMTracer.stats_by_step()

```python
class TestLLMTracerStatsByStep:
    """Test LLMTracer.stats_by_step() method."""

    def test_groups_by_step(db_session):
        """Returns stats grouped by step_name."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=100, step_name="step1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=200, step_name="step1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=300, step_name="step2")

        stats = tracer.stats_by_step()
        assert len(stats) == 2

        step1_stats = next(s for s in stats if s["step"] == "step1")
        assert step1_stats["calls"] == 2

    def test_per_step_metrics(db_session):
        """Each step has its own metrics."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0,
                     step_name="step1", tokens_in=100, cost=0.01)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0,
                     step_name="step2", tokens_in=200, cost=0.02)

        stats = tracer.stats_by_step()
        step1 = next(s for s in stats if s["step"] == "step1")
        step2 = next(s for s in stats if s["step"] == "step2")

        assert step1["total_cost"] == 0.01
        assert step2["total_cost"] == 0.02
```

### 4.5 TracingHooks

```python
class TestTracingHooks:
    """Test TracingHooks integration with LLMTracer."""

    def test_on_row_success_records_trace(db_session):
        """on_row_success calls tracer.record()."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer, model_name="gpt-4", provider="openai")

        hooks.on_row_success(
            step_name="extract",
            idx=0, total=10, latency_ms=100,
            prompt="test prompt",
            tokens_in=50, tokens_out=25, cost=0.01,
            result={"key": "value"}
        )

        traces = tracer.query()
        assert len(traces) == 1
        assert traces[0]["prompt"] == "test prompt"
        assert traces[0]["model"] == "gpt-4"

    def test_on_row_error_records_trace(db_session):
        """on_row_error calls tracer.record() with error."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer)

        hooks.on_row_error(
            step_name="extract",
            idx=0, total=10, latency_ms=100,
            prompt="test prompt",
            tokens_in=50, tokens_out=0, cost=0.0,
            error=ValueError("LLM failed")
        )

        traces = tracer.query()
        assert traces[0]["error"] == "LLM failed"

    def test_model_provider_passed_through(db_session):
        """model_name and provider are stored in traces."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer, model_name="claude-3", provider="anthropic")

        hooks.on_row_success(
            step_name="s", idx=0, total=1, latency_ms=0,
            prompt="p", tokens_in=0, tokens_out=0, cost=0, result={}
        )

        trace = tracer.query()[0]
        assert trace["model"] == "claude-3"
        assert trace["provider"] == "anthropic"
```

---

## 5. test_database.py - Database Abstraction

### 5.1 Database Client Factory

```python
class TestGetDatabaseClient:
    """Test get_database_client() factory."""

    def test_sqlite_by_default(monkeypatch):
        """Returns SQLiteClient when no DATABASE_URL."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        client = get_database_client()
        assert isinstance(client, SQLiteClient)

    def test_postgres_with_postgres_url(monkeypatch):
        """Returns PostgreSQLClient with postgres:// URL."""
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host/db")
        client = get_database_client()
        assert isinstance(client, PostgreSQLClient)

    def test_postgres_with_postgresql_url(monkeypatch):
        """Returns PostgreSQLClient with postgresql:// URL."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/db")
        client = get_database_client()
        assert isinstance(client, PostgreSQLClient)

    def test_sqlite_with_sqlite_url(monkeypatch):
        """Returns SQLiteClient with sqlite:// URL."""
        monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
        client = get_database_client()
        assert isinstance(client, SQLiteClient)
```

### 5.2 Session Management

```python
class TestSessionManagement:
    """Test session management functions."""

    def test_init_database_creates_tables(tmp_path, monkeypatch):
        """init_database() creates all SQLModel tables."""
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

        init_database()

        # Check tables exist
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "llm_traces" in tables

    def test_managed_session_commits_on_success(db_session):
        """managed_session commits on successful exit."""
        with managed_session() as session:
            trace = LLMTrace(workflow_id="w", step_name="s", model="m",
                            prompt="p", response="r")
            session.add(trace)

        # Verify committed
        with managed_session() as session:
            count = session.query(LLMTrace).count()
        assert count == 1

    def test_managed_session_rollbacks_on_error(db_session):
        """managed_session rollbacks on exception."""
        try:
            with managed_session() as session:
                trace = LLMTrace(workflow_id="w", step_name="s", model="m",
                                prompt="p", response="r")
                session.add(trace)
                raise ValueError("test error")
        except ValueError:
            pass

        # Verify rolled back
        with managed_session() as session:
            count = session.query(LLMTrace).count()
        assert count == 0

    def test_get_session_returns_session():
        """get_session() returns a Session instance."""
        session = get_session()
        assert session is not None
```

### 5.3 Mixins

```python
class TestMixins:
    """Test database model mixins."""

    def test_timestamp_mixin_defaults():
        """TimestampMixin sets created_at and updated_at."""
        class TestModel(TimestampMixin, SQLModel, table=True):
            id: int = Field(primary_key=True)

        model = TestModel(id=1)
        assert model.created_at is not None
        assert model.updated_at is not None

    def test_tenant_mixin_fields():
        """TenantMixin has user_id and workspace_id."""
        class TestModel(TenantMixin, SQLModel, table=True):
            id: int = Field(primary_key=True)

        model = TestModel(id=1, user_id="user-123", workspace_id="ws-456")
        assert model.user_id == "user-123"
        assert model.workspace_id == "ws-456"

    def test_embedding_mixin_stores_bytes():
        """EmbeddingMixin stores embedding as bytes."""
        class TestModel(EmbeddingMixin, SQLModel, table=True):
            id: int = Field(primary_key=True)

        embedding = b"\x00\x01\x02\x03"
        model = TestModel(id=1, embedding=embedding)
        assert model.embedding == embedding

    def test_confidence_mixin_validation():
        """ConfidenceMixin validates confidence 0-1."""
        class TestModel(ConfidenceMixin, SQLModel, table=True):
            id: int = Field(primary_key=True)

        model = TestModel(id=1, confidence=0.85)
        assert model.confidence == 0.85

        with pytest.raises(ValidationError):
            TestModel(id=2, confidence=1.5)  # > 1.0

        with pytest.raises(ValidationError):
            TestModel(id=3, confidence=-0.1)  # < 0.0
```

---

## 6. test_durability.py - DBOS Integration

> **Note:** These tests require DBOS infrastructure and are integration tests.

### 6.1 Step Idempotency

```python
class TestStepIdempotency:
    """Test DBOS step idempotency guarantees."""

    def test_completed_steps_not_reexecuted():
        """Retrieving a completed workflow doesn't re-execute steps."""
        call_count = {"count": 0}

        @DBOS.step()
        def counting_step(x):
            call_count["count"] += 1
            return x * 2

        @DBOS.workflow()
        def test_workflow(items):
            return [counting_step(i) for i in items]

        # First run
        handle = DBOS.start_workflow(test_workflow, [1, 2, 3])
        workflow_id = handle.get_workflow_id()
        handle.get_result()
        count_after_first = call_count["count"]

        # Retrieve same workflow
        handle2 = DBOS.retrieve_workflow(workflow_id)
        handle2.get_result()
        count_after_second = call_count["count"]

        assert count_after_first == count_after_second  # No re-execution
```

### 6.2 Queue Durability

```python
class TestQueueDurability:
    """Test DBOS Queue durability."""

    def test_queued_steps_not_reexecuted():
        """Retrieving workflow with queue doesn't re-execute queued steps."""
        call_count = {"count": 0}
        queue = Queue("test_queue", concurrency=2)

        @DBOS.step()
        def queued_step(x):
            call_count["count"] += 1
            return x

        @DBOS.workflow()
        def test_workflow(items):
            handles = [queue.enqueue(queued_step, i) for i in items]
            return [h.get_result() for h in handles]

        # First run
        handle = DBOS.start_workflow(test_workflow, [1, 2, 3])
        workflow_id = handle.get_workflow_id()
        handle.get_result()
        count_after_first = call_count["count"]

        # Retrieve same workflow
        handle2 = DBOS.retrieve_workflow(workflow_id)
        handle2.get_result()
        count_after_second = call_count["count"]

        assert count_after_first == count_after_second

    def test_queue_respects_concurrency():
        """Queue processes at most N items concurrently."""
        # Track concurrent executions
        concurrent = {"current": 0, "max": 0}

        @DBOS.step()
        def concurrent_step(x):
            concurrent["current"] += 1
            concurrent["max"] = max(concurrent["max"], concurrent["current"])
            time.sleep(0.1)
            concurrent["current"] -= 1
            return x

        queue = Queue("concurrency_test", concurrency=2)

        @DBOS.workflow()
        def test_workflow():
            handles = [queue.enqueue(concurrent_step, i) for i in range(10)]
            return [h.get_result() for h in handles]

        DBOS.start_workflow(test_workflow).get_result()
        assert concurrent["max"] <= 2
```

### 6.3 Error Persistence

```python
class TestErrorPersistence:
    """Test error handling and persistence."""

    def test_step_errors_captured():
        """Step errors are captured in result."""
        @DBOS.step()
        def failing_step():
            raise ValueError("intentional error")

        @DBOS.workflow()
        def test_workflow():
            try:
                return failing_step()
            except Exception as e:
                return {"error": str(e)}

        result = DBOS.start_workflow(test_workflow).get_result()
        assert "error" in result
        assert "intentional error" in result["error"]

    def test_partial_success_preserved():
        """Successful steps before error are preserved."""
        results = []

        @DBOS.step()
        def append_step(x):
            results.append(x)
            if x == 3:
                raise ValueError("fail on 3")
            return x

        @DBOS.workflow()
        def test_workflow():
            outputs = []
            for i in [1, 2, 3, 4]:
                try:
                    outputs.append(append_step(i))
                except Exception:
                    outputs.append(None)
            return outputs

        DBOS.start_workflow(test_workflow).get_result()
        assert 1 in results
        assert 2 in results
```

### 6.4 Crash Recovery

```python
class TestCrashRecovery:
    """Test crash recovery behavior."""

    def test_steps_before_crash_stored():
        """Steps completed before crash are durable."""
        completed_steps = []

        @DBOS.step()
        def durable_step(x):
            completed_steps.append(x)
            return x

        @DBOS.workflow()
        def crashing_workflow(crash_on):
            for i in [1, 2, 3, 4]:
                if i == crash_on:
                    raise RuntimeError("crash")
                durable_step(i)
            return completed_steps

        # Run and crash
        try:
            handle = DBOS.start_workflow(crashing_workflow, 3)
            handle.get_result()
        except RuntimeError:
            pass

        # Steps 1, 2 should be complete
        assert 1 in completed_steps
        assert 2 in completed_steps
        assert 3 not in completed_steps

    def test_retrieve_crashed_workflow_returns_error():
        """Retrieving crashed workflow returns the error."""
        @DBOS.workflow()
        def crashing_workflow():
            raise RuntimeError("intentional crash")

        handle = DBOS.start_workflow(crashing_workflow)
        workflow_id = handle.get_workflow_id()

        try:
            handle.get_result()
        except RuntimeError:
            pass

        # Retrieve should also raise
        handle2 = DBOS.retrieve_workflow(workflow_id)
        with pytest.raises(RuntimeError):
            handle2.get_result()
```

---

## Test Fixtures

```python
# conftest.py

import pytest
import tempfile
import os
from pathlib import Path

@pytest.fixture
def db_session(tmp_path, monkeypatch):
    """Provide a fresh SQLite database for each test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    from kurt_new.db import init_database
    init_database()

    yield

    # Cleanup
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture
def mock_dbos():
    """Mock DBOS for unit tests that don't need real DBOS."""
    from unittest.mock import MagicMock, patch

    with patch("kurt_new.core.llm_step.DBOS") as mock:
        mock.workflow_id = "test-workflow-id"
        mock.step = lambda name: lambda fn: fn
        mock.write_stream = MagicMock()
        mock.set_event = MagicMock()
        yield mock


class MockSchema(BaseModel):
    """Simple schema for tests."""
    field: str = ""
    score: float = 0.0
```

---

## Running Tests

```bash
# Unit tests only (no DBOS required)
pytest tests/test_llm_step.py tests/test_hooks.py tests/test_mocking.py -v

# With database tests (SQLite)
pytest tests/test_tracing.py tests/test_database.py -v

# Integration tests (requires DBOS)
DATABASE_URL=sqlite:///test.db pytest tests/test_durability.py -v

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=kurt_new --cov-report=html
```
