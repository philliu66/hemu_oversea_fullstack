/** 当前已选模板 id 不在列表中时，用 id 自身占位，避免 Select 空白或裸值异常 */
export function withCurrentTemplateOption(
  items: { label: string; value: string }[],
  currentId?: string | null,
) {
  const current = currentId?.trim();
  if (!current || items.some((item) => item.value === current)) {
    return items;
  }
  return [{ label: current, value: current }, ...items];
}
