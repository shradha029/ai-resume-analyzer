import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, PolarAngleAxis, RadialBar, RadialBarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { isNum, scoreColor, statusColors } from "../utils/format";

/** Semi-circular gauge for a 0-100 score. */
export function ScoreGauge({ value, label }) {
  return (
    <div role="img" aria-label={`${label} gauge`} className="relative h-48">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart innerRadius="70%" outerRadius="100%" startAngle={210} endAngle={-30}
          data={[{ name: label, value: isNum(value) ? value : 0 }]}>
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" background cornerRadius={12} fill={scoreColor(value)} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-3xl font-bold" style={{ color: scoreColor(value) }}>{isNum(value) ? `${value.toFixed(0)}%` : "?"}</div>
        <div className="text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}

/** Credit (0-100%) earned for every required skill. */
export function SkillCreditChart({ matches }) {
  const data = matches.map((m) => ({ name: m.skill, credit: Math.round(m.credit * 100), status: m.status }));
  return (
    <div role="img" aria-label="Skill matching bar chart" style={{ height: Math.max(220, data.length * 28 + 40) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} unit="%" />
          <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v) => `${v}%`} />
          <Bar dataKey="credit" radius={[0, 6, 6, 0]}>
            {data.map((d) => <Cell key={d.name} fill={statusColors[d.status]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MatchedMissingPie({ matches }) {
  const count = (s) => matches.filter((m) => m.status === s).length;
  const data = ["matched", "partial", "missing"].map((s) => ({ name: s, value: count(s) })).filter((d) => d.value > 0);
  return (
    <div role="img" aria-label="Matched vs missing skills chart" className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={45} outerRadius={80} paddingAngle={2} label>
            {data.map((d) => <Cell key={d.name} fill={statusColors[d.name]} />)}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Required skills per category, split by match status. */
export function CategoryChart({ matches }) {
  const by = {};
  matches.forEach((m) => {
    const c = by[m.category] || (by[m.category] = { category: m.category, matched: 0, partial: 0, missing: 0 });
    c[m.status] += 1;
  });
  return (
    <div role="img" aria-label="Requirement category comparison chart" className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={Object.values(by)}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="category" interval={0} angle={-30} textAnchor="end" height={55} tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Legend />
          {["matched", "partial", "missing"].map((s) => <Bar key={s} dataKey={s} stackId="a" fill={statusColors[s]} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Resume quality: percentage earned in each scoring component (section completeness etc.). */
export function QualityChart({ quality }) {
  const data = Object.values(quality.components).map((c) => ({ name: c.label, percent: c.percent }));
  return (
    <div role="img" aria-label="Resume section completeness chart" className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" domain={[0, 100]} unit="%" />
          <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v) => `${v}%`} />
          <Bar dataKey="percent" fill="#7048e8" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Match-score components that could be scored (unknown ones are listed in the page text, not drawn as 0). */
export function ComponentChart({ components }) {
  const data = Object.entries(components).filter(([, c]) => isNum(c.score)).map(([k, c]) => ({ name: k, score: c.score }));
  return (
    <div role="img" aria-label="Match score components chart" className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" interval={0} angle={-30} textAnchor="end" height={55} tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Bar dataKey="score" fill="#4c6ef5" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
