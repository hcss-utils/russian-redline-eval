function matrix(m){
    /* DERIVED, not inferred. This used to invent the off-diagonal cells from fixed ratios
       (fa*0.65, rest*0.6) with a remainder that could render NEGATIVE counts. The producer
       now emits `cm` counted from every decision record; rows are Ref None/RLS/NTS and
       columns Pred None/RLS/NTS, over all repetitions. */
    if (m.cm) return m.cm;
    return [[0,0,0],[0,0,0],[0,0,0]];
}