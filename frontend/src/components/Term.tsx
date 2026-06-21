import { GLOSSARY } from "../lib/glossary";

interface Props {
  k: keyof typeof GLOSSARY | string;
  children: React.ReactNode;
}

/** 용어에 ⓘ 를 붙이고, 가리키면 초보용 설명을 보여준다(glossary). */
export function Term({ k, children }: Props) {
  const tip = GLOSSARY[k];
  return (
    <span className="gloss" title={tip}>
      {children}
      <sup className="gloss-i">ⓘ</sup>
    </span>
  );
}
