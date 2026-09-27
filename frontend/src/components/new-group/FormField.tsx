export function FormField({
  label,
  required,
  optional,
  small,
  children,
}: {
  label: string;
  required?: boolean;
  optional?: boolean;
  small?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className={`block ${small ? "text-xs text-gray-500" : "text-sm font-medium text-gray-700"} mb-1`}>
        {label}{" "}
        {required && <span className="text-red-500">*</span>}
        {optional && <span className="text-gray-400 font-normal">(optional)</span>}
      </label>
      {children}
    </div>
  );
}
