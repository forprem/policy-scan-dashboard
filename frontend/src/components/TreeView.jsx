import { useState } from "react";

function TreeNode({ node, name, onSelect }) {
  const [open, setOpen] = useState(false);

  const isFile = node.__issues;

  return (
    <div style={{ marginLeft: "10px" }}>
      <div
        style={{ cursor: "pointer" }}
        onClick={() => {
          if (isFile) onSelect(node.__issues);
          else setOpen(!open);
        }}
      >
        {isFile ? "📄" : "📁"} {name}
      </div>

      {open &&
        Object.keys(node)
          .filter(k => k !== "__issues")
          .map((k, i) => (
            <TreeNode key={i} node={node[k]} name={k} onSelect={onSelect} />
          ))}
    </div>
  );
}

// helper
export const buildTree = (findings) => {
  const tree = {};

  findings.forEach(f => {
    const parts = f.file.split("/");
    let current = tree;

    parts.forEach((part, i) => {
      if (!current[part]) current[part] = {};
      current = current[part];

      if (i === parts.length - 1) {
        current.__issues = (current.__issues || []).concat(f);
      }
    });
  });

  return tree;
};

export default TreeNode;