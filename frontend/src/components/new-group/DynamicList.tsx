export function DynamicList<T>({
  items,
  onAdd,
  onRemove,
  addLabel,
  itemLabel = "Group",
  renderItem,
}: {
  items: T[];
  onAdd: () => void;
  onRemove: (i: number) => void;
  addLabel: string;
  itemLabel?: string;
  renderItem: (item: T, i: number) => React.ReactNode;
}) {
  return (
    <div>
      {items.map((item, i) => (
        <div key={i} className="border border-gray-100 rounded-lg p-4 mb-3 space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-400">{itemLabel} {i + 1}</span>
            <button onClick={() => onRemove(i)} className="text-xs text-gray-400 hover:text-red-500">
              Remove
            </button>
          </div>
          {renderItem(item, i)}
        </div>
      ))}
      <button onClick={onAdd} className="text-sm text-blue-600 hover:underline">
        {addLabel}
      </button>
    </div>
  );
}
