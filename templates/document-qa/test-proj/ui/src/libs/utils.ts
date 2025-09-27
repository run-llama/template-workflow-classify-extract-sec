export function toHumanResponseRawEvent(str: string) {
  return {
    __is_pydantic: true,
    value: { _data: { response: str } },
    qualified_name: "workflows.events.HumanResponseEvent",
  };
}
