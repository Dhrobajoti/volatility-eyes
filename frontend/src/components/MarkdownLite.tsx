import { Fragment } from "react";

/**
 * Minimal, dependency-free renderer for the handful of markdown constructs
 * the local model actually produces (headings, bold, bullet lists,
 * paragraphs). Deliberately not a full markdown parser and deliberately not
 * `dangerouslySetInnerHTML` - this builds React elements directly, so there's
 * no HTML-injection surface even though the text originates from an LLM.
 */

function renderInline(text: string, keyPrefix: string) {
  const parts = text.split(/(\*\*.+?\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <Fragment key={`${keyPrefix}-${i}`}>{part}</Fragment>;
  });
}

export function MarkdownLite({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let listBuffer: string[] = [];

  const flushList = (key: string) => {
    if (listBuffer.length === 0) return;
    blocks.push(
      <ul key={key}>
        {listBuffer.map((item, i) => (
          <li key={i}>{renderInline(item, `${key}-li-${i}`)}</li>
        ))}
      </ul>,
    );
    listBuffer = [];
  };

  lines.forEach((line, i) => {
    const heading = /^(#{1,4})\s+(.*)/.exec(line);
    const listItem = /^\s*[-*]\s+(.*)/.exec(line);

    if (listItem) {
      listBuffer.push(listItem[1]);
      return;
    }
    flushList(`list-${i}`);

    if (heading) {
      const level = heading[1].length;
      const content = renderInline(heading[2], `h-${i}`);
      if (level <= 2) blocks.push(<h3 key={i}>{content}</h3>);
      else blocks.push(<h4 key={i}>{content}</h4>);
    } else if (line.trim() === "") {
      // blank line - paragraph break, nothing to render
    } else {
      blocks.push(<p key={i}>{renderInline(line, `p-${i}`)}</p>);
    }
  });
  flushList("list-end");

  return <>{blocks}</>;
}
