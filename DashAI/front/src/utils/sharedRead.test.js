import { sharedRead } from "./sharedRead";

const later = () => {
  let resolve;
  let reject;
  const promise = new Promise((ok, fail) => {
    resolve = ok;
    reject = fail;
  });
  return { promise, resolve, reject };
};

it("keeps only the newest read when two cross", async () => {
  const old = later();
  const read = jest
    .fn()
    .mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce("new");
  const store = sharedRead({ read, empty: null });

  store.refresh();
  await store.refresh();
  old.resolve("old");
  await old.promise;

  expect(store.get()).toEqual({ data: "new", error: null });
});

it("fresh() waits for the newest read, even one started meanwhile", async () => {
  const old = later();
  const read = jest
    .fn()
    .mockReturnValueOnce(old.promise)
    .mockResolvedValueOnce("new");
  const store = sharedRead({ read, empty: null });

  const answer = store.fresh();
  store.refresh(); // e.g. a plugin changed
  old.reject(new Error("offline")); // the older one failing doesn't count

  await expect(answer).resolves.toBe("new");
  expect(read).toHaveBeenCalledTimes(2);
});

it("fresh() shares a read on its way and rejects if it fails, keeping the data", async () => {
  const read = jest
    .fn()
    .mockResolvedValueOnce("first")
    .mockRejectedValueOnce(new Error("offline"));
  const store = sharedRead({ read, empty: null });
  await store.fresh();

  const failure = store.fresh();
  const shared = store.fresh();

  await expect(failure).rejects.toThrow("offline");
  await expect(shared).rejects.toThrow("offline");
  expect(read).toHaveBeenCalledTimes(2);
  expect(store.get()).toMatchObject({ data: "first" });
  expect(store.get().error.message).toBe("offline");
});

it.each([
  [false, 1],
  [true, 2],
])(
  "with revalidate %s, three views mounting read %i times",
  async (revalidate, reads) => {
    const read = jest.fn().mockResolvedValue("data");
    const store = sharedRead({ read, empty: null, revalidate });

    store.mounted();
    store.mounted(); // while the first read is on its way: shares it
    await store.fresh();
    store.mounted(); // later

    expect(read).toHaveBeenCalledTimes(reads);
  },
);

it("reads again on its window event", async () => {
  const read = jest.fn().mockResolvedValue("data");
  const store = sharedRead({ read, empty: null, refreshOn: "test:changed" });

  window.dispatchEvent(new Event("test:changed"));
  await store.fresh();

  expect(read).toHaveBeenCalledTimes(1);
  expect(store.get().data).toBe("data");
});
